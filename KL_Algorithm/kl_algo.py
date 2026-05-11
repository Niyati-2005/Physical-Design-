import argparse
import csv
from math import inf


def load_graph_from_csv(csv_path):
    """
    Load an undirected weighted graph from a CSV edge list.

    Expected columns:
    - source,target
    - source,target,weight

    Header names supported:
    - source/src/from
    - target/dst/to
    - weight/w
    """
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file must contain a header row.")

        field_map = {name.strip().lower(): name for name in reader.fieldnames}

        source_key = next(
            (field_map[name] for name in ("source", "src", "from") if name in field_map),
            None,
        )
        target_key = next(
            (field_map[name] for name in ("target", "dst", "to") if name in field_map),
            None,
        )
        weight_key = next(
            (field_map[name] for name in ("weight", "w") if name in field_map),
            None,
        )

        if source_key is None or target_key is None:
            raise ValueError(
                "CSV header must include source and target columns "
                "(for example: source,target,weight)."
            )

        graph = {}

        for line_number, row in enumerate(reader, start=2):
            source = row[source_key].strip()
            target = row[target_key].strip()

            if not source or not target:
                raise ValueError(f"Missing node name on CSV line {line_number}.")

            weight = 1.0
            if weight_key is not None and row[weight_key].strip():
                weight = float(row[weight_key])

            graph.setdefault(source, {})
            graph.setdefault(target, {})

            # Sum repeated edges if they appear multiple times.
            graph[source][target] = graph[source].get(target, 0.0) + weight
            graph[target][source] = graph[target].get(source, 0.0) + weight

    if not graph:
        raise ValueError("CSV file did not contain any edges.")

    return graph


def kernighan_lin(graph, max_passes=100):
    nodes = list(graph.keys())
    node_count = len(nodes)

    if node_count % 2 != 0:
        raise ValueError(
            "Kernighan-Lin requires an even number of nodes for equal partitioning."
        )

    partition_a = set(nodes[: node_count // 2])
    partition_b = set(nodes[node_count // 2 :])

    def edge_weight(node_u, node_v):
        return graph.get(node_u, {}).get(node_v, 0.0)

    def compute_d_values(group_a, group_b):
        d_values = {}

        for node in group_a:
            external = sum(edge_weight(node, other) for other in group_b)
            internal = sum(edge_weight(node, other) for other in group_a if other != node)
            d_values[node] = external - internal

        for node in group_b:
            external = sum(edge_weight(node, other) for other in group_a)
            internal = sum(edge_weight(node, other) for other in group_b if other != node)
            d_values[node] = external - internal

        return d_values

    def cut_cost(group_a, group_b):
        return sum(edge_weight(node_a, node_b) for node_a in group_a for node_b in group_b)

    for _ in range(max_passes):
        d_values = compute_d_values(partition_a, partition_b)
        unlocked_a = set(partition_a)
        unlocked_b = set(partition_b)
        gains = []
        chosen_pairs = []

        for _ in range(node_count // 2):
            best_gain = -inf
            best_pair = None

            for node_a in unlocked_a:
                for node_b in unlocked_b:
                    gain = d_values[node_a] + d_values[node_b] - 2 * edge_weight(node_a, node_b)
                    if gain > best_gain:
                        best_gain = gain
                        best_pair = (node_a, node_b)

            if best_pair is None:
                break

            node_a, node_b = best_pair
            gains.append(best_gain)
            chosen_pairs.append(best_pair)
            unlocked_a.remove(node_a)
            unlocked_b.remove(node_b)

            for remaining_a in unlocked_a:
                d_values[remaining_a] += (
                    2 * edge_weight(remaining_a, node_a)
                    - 2 * edge_weight(remaining_a, node_b)
                )

            for remaining_b in unlocked_b:
                d_values[remaining_b] += (
                    2 * edge_weight(remaining_b, node_b)
                    - 2 * edge_weight(remaining_b, node_a)
                )

        best_prefix_gain = -inf
        running_gain = 0.0
        best_prefix_index = -1

        for index, gain in enumerate(gains):
            running_gain += gain
            if running_gain > best_prefix_gain:
                best_prefix_gain = running_gain
                best_prefix_index = index

        if best_prefix_gain <= 0:
            break

        for index in range(best_prefix_index + 1):
            node_a, node_b = chosen_pairs[index]
            partition_a.remove(node_a)
            partition_b.remove(node_b)
            partition_a.add(node_b)
            partition_b.add(node_a)

    return partition_a, partition_b, cut_cost(partition_a, partition_b)


def write_output_csv(output_path, partition_a, partition_b):
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["node", "partition"])

        for node in sorted(partition_a):
            writer.writerow([node, "A"])

        for node in sorted(partition_b):
            writer.writerow([node, "B"])


def main():
    parser = argparse.ArgumentParser(
        description="Run the Kernighan-Lin balanced graph partitioning algorithm on a CSV edge list."
    )
    parser.add_argument("input_csv", help="Path to the input CSV edge list.")
    parser.add_argument(
        "-o",
        "--output-csv",
        help="Optional path to save the partition assignment CSV.",
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=100,
        help="Maximum number of KL improvement passes.",
    )
    args = parser.parse_args()

    graph = load_graph_from_csv(args.input_csv)
    partition_a, partition_b, total_cut_cost = kernighan_lin(graph, max_passes=args.max_passes)

    print("Partition A:", ", ".join(sorted(partition_a)))
    print("Partition B:", ", ".join(sorted(partition_b)))
    print("Cut cost:", total_cut_cost)

    if args.output_csv:
        write_output_csv(args.output_csv, partition_a, partition_b)
        print("Partition CSV written to:", args.output_csv)


if __name__ == "__main__":
    main()
