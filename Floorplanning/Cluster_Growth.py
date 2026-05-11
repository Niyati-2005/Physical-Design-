import argparse
import csv
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class Module:
    name: str
    width: int
    height: int


@dataclass(frozen=True)
class Placement:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


def load_modules_from_csv(csv_path: str) -> Dict[str, Module]:
    modules: Dict[str, Module] = {}
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("Module CSV must contain a header row.")

        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        name_key = field_map.get("module") or field_map.get("name")
        width_key = field_map.get("width") or field_map.get("w")
        height_key = field_map.get("height") or field_map.get("h")

        if not name_key or not width_key or not height_key:
            raise ValueError("Module CSV must contain module,width,height columns.")

        for line_number, row in enumerate(reader, start=2):
            name = row[name_key].strip()
            if not name:
                raise ValueError(f"Missing module name on CSV line {line_number}.")

            modules[name] = Module(
                name=name,
                width=int(row[width_key]),
                height=int(row[height_key]),
            )

    if not modules:
        raise ValueError("Module CSV did not contain any modules.")

    return modules


def load_nets_from_csv(csv_path: str) -> Dict[str, Tuple[str, ...]]:
    nets: Dict[str, Tuple[str, ...]] = {}
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("Net CSV must contain a header row.")

        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        net_key = field_map.get("net") or field_map.get("name")
        cells_key = field_map.get("cells") or field_map.get("modules") or field_map.get("pins")

        if not net_key or not cells_key:
            raise ValueError("Net CSV must contain net,cells columns.")

        for line_number, row in enumerate(reader, start=2):
            net_name = row[net_key].strip()
            cell_text = row[cells_key].strip()
            if not net_name:
                raise ValueError(f"Missing net name on CSV line {line_number}.")
            cells = tuple(token.strip() for token in cell_text.replace(",", " ").split() if token.strip())
            if len(cells) < 2:
                raise ValueError(
                    f"Net '{net_name}' on CSV line {line_number} must connect at least two modules."
                )
            nets[net_name] = cells

    if not nets:
        raise ValueError("Net CSV did not contain any nets.")

    return nets


def incident_nets(module_name: str, nets: Dict[str, Sequence[str]]) -> List[str]:
    return [net_name for net_name, pins in nets.items() if module_name in pins]


def classify_nets(
    module_name: str,
    placed: Sequence[str],
    unplaced: Sequence[str],
    nets: Dict[str, Sequence[str]],
) -> Tuple[List[str], List[str], List[str]]:
    new_nets: List[str] = []
    terminating_nets: List[str] = []
    continuing_nets: List[str] = []

    placed_set = set(placed)
    unplaced_set = set(unplaced)

    for net_name in incident_nets(module_name, nets):
        pins = set(nets[net_name])
        placed_pins = pins & placed_set
        unplaced_pins = pins & unplaced_set

        if not placed_pins:
            new_nets.append(net_name)
        elif len(unplaced_pins) == 1 and module_name in unplaced_pins:
            terminating_nets.append(net_name)
        else:
            continuing_nets.append(net_name)

    return sorted(new_nets), sorted(terminating_nets), sorted(continuing_nets)


def generate_linear_order(
    modules: Dict[str, Module],
    nets: Dict[str, Sequence[str]],
    start_module: str,
) -> Tuple[List[str], List[Dict[str, object]]]:
    if start_module not in modules:
        raise ValueError(f"Unknown start module: {start_module}")

    ordered = [start_module]
    unplaced = [name for name in modules if name != start_module]
    history: List[Dict[str, object]] = []

    start_new, start_term, start_cont = classify_nets(
        start_module, [], list(modules.keys()), nets
    )
    history.append(
        {
            "iteration": 0,
            "selected": start_module,
            "new_nets": start_new,
            "terminating_nets": start_term,
            "continuing_nets": start_cont,
            "gain": len(start_term) - len(start_new),
        }
    )

    iteration = 1
    while unplaced:
        candidates = []
        for module_name in unplaced:
            new_nets, terminating_nets, continuing_nets = classify_nets(
                module_name, ordered, unplaced, nets
            )
            gain = len(terminating_nets) - len(new_nets)
            candidates.append(
                {
                    "iteration": iteration,
                    "module": module_name,
                    "new_nets": new_nets,
                    "terminating_nets": terminating_nets,
                    "continuing_nets": continuing_nets,
                    "gain": gain,
                }
            )

        candidates.sort(
            key=lambda item: (
                -item["gain"],
                -len(item["continuing_nets"]),
                item["module"],
            )
        )
        selected = candidates[0]
        ordered.append(selected["module"])
        unplaced.remove(selected["module"])
        history.append(
            {
                "iteration": iteration,
                "selected": selected["module"],
                "new_nets": selected["new_nets"],
                "terminating_nets": selected["terminating_nets"],
                "continuing_nets": selected["continuing_nets"],
                "gain": selected["gain"],
                "candidates": candidates,
            }
        )
        iteration += 1

    return ordered, history


def overlap(a: Placement, b: Placement) -> bool:
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )


def module_centers(placements: Dict[str, Placement]) -> Dict[str, Tuple[float, float]]:
    return {name: placement.center for name, placement in placements.items()}


def partial_hpwl(
    placements: Dict[str, Placement], nets: Dict[str, Sequence[str]], weight_by_net: bool = False
) -> float:
    centers = module_centers(placements)
    total = 0.0

    for net_name, pins in nets.items():
        present = [centers[module_name] for module_name in pins if module_name in centers]
        if len(present) < 2:
            continue

        xs = [point[0] for point in present]
        ys = [point[1] for point in present]
        hpwl = (max(xs) - min(xs)) + (max(ys) - min(ys))
        total += hpwl if not weight_by_net else hpwl * len(pins)

    return total


def bounding_box_area(placements: Dict[str, Placement]) -> int:
    min_x = min(placement.x for placement in placements.values())
    min_y = min(placement.y for placement in placements.values())
    max_x = max(placement.x + placement.width for placement in placements.values())
    max_y = max(placement.y + placement.height for placement in placements.values())
    return (max_x - min_x) * (max_y - min_y)


def candidate_positions(
    module: Module, placed_modules: Dict[str, Placement]
) -> List[Tuple[int, int, int, int]]:
    if not placed_modules:
        return [(0, 0, module.width, module.height)]

    candidates = set()
    orientations = {(module.width, module.height)}
    if module.width != module.height:
        orientations.add((module.height, module.width))

    for placement in placed_modules.values():
        for width, height in orientations:
            candidates.add((placement.x + placement.width, placement.y, width, height))
            candidates.add((placement.x - width, placement.y, width, height))
            candidates.add((placement.x, placement.y + placement.height, width, height))
            candidates.add((placement.x, placement.y - height, width, height))

    return sorted(candidates)


def choose_best_placement(
    module: Module,
    current_placements: Dict[str, Placement],
    nets: Dict[str, Sequence[str]],
    alpha: float = 1.0,
    beta: float = 1.0,
) -> Placement:
    best_choice = None
    best_cost = None

    for x, y, width, height in candidate_positions(module, current_placements):
        trial = Placement(x=x, y=y, width=width, height=height)
        if any(overlap(trial, placed) for placed in current_placements.values()):
            continue

        trial_placements = dict(current_placements)
        trial_placements[module.name] = trial
        cost = alpha * bounding_box_area(trial_placements) + beta * partial_hpwl(
            trial_placements, nets
        )

        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_choice = trial

    if best_choice is None:
        raise RuntimeError(f"Could not find a legal placement for module {module.name}.")

    return best_choice


def construct_floorplan(
    ordered_modules: Sequence[str],
    modules: Dict[str, Module],
    nets: Dict[str, Sequence[str]],
) -> Dict[str, Placement]:
    placements: Dict[str, Placement] = {}
    for module_name in ordered_modules:
        placement = choose_best_placement(modules[module_name], placements, nets)
        placements[module_name] = placement
    return placements


def normalize_placements(placements: Dict[str, Placement]) -> Dict[str, Placement]:
    min_x = min(placement.x for placement in placements.values())
    min_y = min(placement.y for placement in placements.values())
    return {
        name: Placement(
            x=placement.x - min_x,
            y=placement.y - min_y,
            width=placement.width,
            height=placement.height,
        )
        for name, placement in placements.items()
    }


def render_ascii_floorplan(placements: Dict[str, Placement]) -> str:
    normalized = normalize_placements(placements)
    max_x = max(placement.x + placement.width for placement in normalized.values())
    max_y = max(placement.y + placement.height for placement in normalized.values())

    grid = [["." for _ in range(max_x)] for _ in range(max_y)]
    for name, placement in normalized.items():
        for y in range(placement.y, placement.y + placement.height):
            for x in range(placement.x, placement.x + placement.width):
                grid[max_y - 1 - y][x] = name

    return "\n".join(" ".join(row) for row in grid)


def print_ordering_history(history: Sequence[Dict[str, object]]) -> None:
    print("Linear Ordering Trace")
    print("-" * 80)
    for entry in history:
        print(
            f"Iteration {entry['iteration']}: selected={entry['selected']}, "
            f"gain={entry['gain']}, "
            f"new={entry['new_nets']}, "
            f"terminating={entry['terminating_nets']}, "
            f"continuing={entry['continuing_nets']}"
        )
        if "candidates" in entry:
            for candidate in entry["candidates"]:
                print(
                    f"  candidate {candidate['module']}: "
                    f"gain={candidate['gain']}, "
                    f"new={candidate['new_nets']}, "
                    f"terminating={candidate['terminating_nets']}, "
                    f"continuing={candidate['continuing_nets']}"
                )
    print()


def print_floorplan(placements: Dict[str, Placement], nets: Dict[str, Sequence[str]]) -> None:
    normalized = normalize_placements(placements)
    print("Floorplan Coordinates")
    print("-" * 80)
    for module_name in sorted(normalized):
        placement = normalized[module_name]
        print(
            f"{module_name}: x={placement.x}, y={placement.y}, "
            f"w={placement.width}, h={placement.height}"
        )
    print()
    print("Floorplan Metrics")
    print("-" * 80)
    print(f"Bounding-box area: {bounding_box_area(normalized)}")
    print(f"Partial HPWL: {partial_hpwl(normalized, nets)}")
    print()
    print("ASCII Floorplan")
    print("-" * 80)
    print(render_ascii_floorplan(normalized))
    print()


def demo_example() -> None:
    modules = {
        "A": Module("A", 2, 2),
        "B": Module("B", 2, 2),
        "C": Module("C", 2, 2),
        "D": Module("D", 2, 2),
        "E": Module("E", 2, 2),
    }

    nets = {
        "N1": ("A", "B"),
        "N2": ("A", "D"),
        "N3": ("A", "C", "E"),
        "N4": ("B", "D"),
        "N5": ("C", "D", "E"),
        "N6": ("D", "E"),
    }

    order, history = generate_linear_order(modules, nets, start_module="A")
    placements = construct_floorplan(order, modules, nets)

    print("Cluster Growth Demo")
    print("=" * 80)
    print("Linear ordering:", " -> ".join(order))
    print()
    print_ordering_history(history)
    print_floorplan(placements, nets)


def run_from_csv(modules_csv: str, nets_csv: str, start_module: str) -> None:
    modules = load_modules_from_csv(modules_csv)
    nets = load_nets_from_csv(nets_csv)

    unknown_modules = sorted(
        {module_name for pins in nets.values() for module_name in pins if module_name not in modules}
    )
    if unknown_modules:
        raise ValueError(f"Nets reference unknown modules: {', '.join(unknown_modules)}")

    order, history = generate_linear_order(modules, nets, start_module=start_module)
    placements = construct_floorplan(order, modules, nets)

    print("Cluster Growth From CSV")
    print("=" * 80)
    print("Linear ordering:", " -> ".join(order))
    print()
    print_ordering_history(history)
    print_floorplan(placements, nets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Construct a floorplan using cluster growth and linear ordering."
    )
    parser.add_argument("--modules-csv", help="Path to CSV containing module,width,height.")
    parser.add_argument("--nets-csv", help="Path to CSV containing net,cells.")
    parser.add_argument(
        "--start-module",
        default="A",
        help="Module to place first when generating the linear ordering.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the built-in slide example.",
    )
    args = parser.parse_args()

    if args.demo or (not args.modules_csv and not args.nets_csv):
        demo_example()
    elif args.modules_csv and args.nets_csv:
        run_from_csv(args.modules_csv, args.nets_csv, args.start_module)
    else:
        raise SystemExit("Provide both --modules-csv and --nets-csv, or use --demo.")
