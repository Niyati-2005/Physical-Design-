import argparse
import csv
import math
import re


def split_cells(cell_text):
    return [token for token in re.split(r"[\s,;]+", cell_text.strip()) if token]


def load_netlist_from_csv(csv_path):
    """
    Load a hypergraph/netlist from CSV.

    Expected formats:
    - net,cells
    - net,cells,weight

    Example:
        net,cells,weight
        a,"2 1",1
        b,"2 1 3",1
    """
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file must contain a header row.")

        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        net_key = next((field_map[name] for name in ("net", "name") if name in field_map), None)
        cells_key = next(
            (field_map[name] for name in ("cells", "nodes", "pins") if name in field_map),
            None,
        )
        weight_key = next(
            (field_map[name] for name in ("weight", "w") if name in field_map),
            None,
        )

        if net_key is None or cells_key is None:
            raise ValueError(
                "CSV header must include net and cells columns "
                "(for example: net,cells,weight)."
            )

        nets = []
        all_cells = set()

        for line_number, row in enumerate(reader, start=2):
            net_name = row[net_key].strip()
            if not net_name:
                raise ValueError(f"Missing net name on CSV line {line_number}.")

            cells = split_cells(row[cells_key])
            if len(cells) < 2:
                raise ValueError(
                    f"Net '{net_name}' on CSV line {line_number} must connect at least two cells."
                )

            weight = 1.0
            if weight_key is not None and row[weight_key].strip():
                weight = float(row[weight_key])

            nets.append({"name": net_name, "cells": tuple(cells), "weight": weight})
            all_cells.update(cells)

    if not nets:
        raise ValueError("CSV file did not contain any nets.")

    return sorted(all_cells), nets


def build_cell_to_nets(cells, nets):
    cell_to_nets = {cell: [] for cell in cells}
    for net_index, net in enumerate(nets):
        for cell in net["cells"]:
            cell_to_nets[cell].append(net_index)
    return cell_to_nets


def initial_partition(cells):
    midpoint = len(cells) // 2
    return set(cells[:midpoint]), set(cells[midpoint:])


def net_is_cut(net_cells, partition_a):
    in_a = any(cell in partition_a for cell in net_cells)
    in_b = any(cell not in partition_a for cell in net_cells)
    return in_a and in_b


def cut_cost(nets, partition_a):
    total = 0.0
    for net in nets:
        if net_is_cut(net["cells"], partition_a):
            total += net["weight"]
    return total


def count_net_sides(net_cells, partition_a):
    from_a = sum(1 for cell in net_cells if cell in partition_a)
    from_b = len(net_cells) - from_a
    return from_a, from_b


def gain_contribution_for_cell(cell, net, partition_a):
    from_a, from_b = count_net_sides(net["cells"], partition_a)
    weight = net["weight"]
    cell_in_a = cell in partition_a

    if cell_in_a:
        fs = weight if from_a == 1 else 0.0
        te = weight if from_b == 0 else 0.0
    else:
        fs = weight if from_b == 1 else 0.0
        te = weight if from_a == 0 else 0.0

    return fs - te


def compute_initial_gains(cells, nets, cell_to_nets, partition_a):
    gains = {}
    for cell in cells:
        gains[cell] = sum(
            gain_contribution_for_cell(cell, nets[net_index], partition_a)
            for net_index in cell_to_nets[cell]
        )
    return gains


def allowed_partition_size_range(total_cells, balance_tolerance):
    lower = total_cells // 2
    upper = math.ceil(total_cells / 2)
    return lower - balance_tolerance, upper + balance_tolerance


def can_move(cell, partition_a, total_cells, balance_tolerance):
    min_size, max_size = allowed_partition_size_range(total_cells, balance_tolerance)

    if cell in partition_a:
        new_a_size = len(partition_a) - 1
    else:
        new_a_size = len(partition_a) + 1

    new_b_size = total_cells - new_a_size
    return (
        min_size <= new_a_size <= max_size
        and min_size <= new_b_size <= max_size
    )


def apply_move(cell, partition_a):
    if cell in partition_a:
        partition_a.remove(cell)
    else:
        partition_a.add(cell)


def critical_nets(cell, nets, cell_to_nets):
    return cell_to_nets[cell]


def update_neighbor_gains(moved_cell, gains, status, partition_a, nets, cell_to_nets):
    for net_index in critical_nets(moved_cell, nets, cell_to_nets):
        net = nets[net_index]
        for cell in net["cells"]:
            if cell == moved_cell or status[cell] != "FREE":
                continue
            gains[cell] = sum(
                gain_contribution_for_cell(cell, nets[neighbor_net_index], partition_a)
                for neighbor_net_index in cell_to_nets[cell]
            )


def fiduccia_mattheyses(cells, nets, max_passes=100, balance_tolerance=0):
    if len(cells) < 2:
        raise ValueError("Netlist must contain at least two cells.")

    cell_to_nets = build_cell_to_nets(cells, nets)
    partition_a, partition_b = initial_partition(cells)
    pass_history = []

    for pass_number in range(1, max_passes + 1):
        current_partition_a = set(partition_a)
        status = {cell: "FREE" for cell in cells}
        gains = compute_initial_gains(cells, nets, cell_to_nets, current_partition_a)
        move_sequence = []

        while any(state == "FREE" for state in status.values()):
            best_cell = None
            best_gain = None

            for cell in cells:
                if status[cell] != "FREE":
                    continue
                if not can_move(cell, current_partition_a, len(cells), balance_tolerance):
                    continue

                gain = gains[cell]
                if best_gain is None or gain > best_gain:
                    best_gain = gain
                    best_cell = cell

            if best_cell is None:
                break

            move_from = "A" if best_cell in current_partition_a else "B"
            move_sequence.append((best_cell, best_gain, move_from))
            apply_move(best_cell, current_partition_a)
            status[best_cell] = "FIXED"
            update_neighbor_gains(
                best_cell,
                gains,
                status,
                current_partition_a,
                nets,
                cell_to_nets,
            )

        best_prefix_gain = 0.0
        running_gain = 0.0
        best_prefix_index = -1

        for index, (_, gain, _) in enumerate(move_sequence):
            running_gain += gain
            if running_gain > best_prefix_gain:
                best_prefix_gain = running_gain
                best_prefix_index = index

        if best_prefix_index == -1:
            pass_history.append(
                {
                    "pass": pass_number,
                    "gain": 0.0,
                    "moves_committed": 0,
                    "cut_cost": cut_cost(nets, partition_a),
                }
            )
            break

        for index in range(best_prefix_index + 1):
            cell, _, _ = move_sequence[index]
            apply_move(cell, partition_a)

        partition_b = set(cells) - partition_a
        current_cut = cut_cost(nets, partition_a)
        pass_history.append(
            {
                "pass": pass_number,
                "gain": best_prefix_gain,
                "moves_committed": best_prefix_index + 1,
                "cut_cost": current_cut,
            }
        )

    return partition_a, partition_b, cut_cost(nets, partition_a), pass_history


def write_output_csv(output_path, partition_a, partition_b):
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["cell", "partition"])

        for cell in sorted(partition_a):
            writer.writerow([cell, "A"])

        for cell in sorted(partition_b):
            writer.writerow([cell, "B"])


def main():
    parser = argparse.ArgumentParser(
        description="Run the Fiduccia-Mattheyses algorithm on a netlist CSV."
    )
    parser.add_argument("input_csv", help="Path to the input netlist CSV.")
    parser.add_argument(
        "-o",
        "--output-csv",
        help="Optional path to save the final partition assignment CSV.",
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=100,
        help="Maximum number of FM improvement passes.",
    )
    parser.add_argument(
        "--balance-tolerance",
        type=int,
        default=0,
        help="Allowed size deviation from a perfectly balanced partition.",
    )
    args = parser.parse_args()

    cells, nets = load_netlist_from_csv(args.input_csv)
    partition_a, partition_b, total_cut_cost, pass_history = fiduccia_mattheyses(
        cells,
        nets,
        max_passes=args.max_passes,
        balance_tolerance=args.balance_tolerance,
    )

    print("Final Partition A:", ", ".join(sorted(partition_a)))
    print("Final Partition B:", ", ".join(sorted(partition_b)))
    print("Final Cut Cost:", total_cut_cost)
    print()
    print("Pass Summary:")
    for entry in pass_history:
        print(
            f"Pass {entry['pass']}: "
            f"gain={entry['gain']}, "
            f"moves={entry['moves_committed']}, "
            f"cut_cost={entry['cut_cost']}"
        )

    if args.output_csv:
        write_output_csv(args.output_csv, partition_a, partition_b)
        print()
        print("Partition CSV written to:", args.output_csv)


if __name__ == "__main__":
    main()
