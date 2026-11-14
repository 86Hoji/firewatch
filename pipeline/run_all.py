import importlib
import sys
import time

STEPS = ["01_download", "02_clean", "02b_outage", "03_grid", "04_landcover", "04b_burned_area", "experiments", "05_calibrate", "06_harmonize",
         "07_validate", "07b_validation_package", "08_export_web"]


def main(argv):
    steps = [s for s in STEPS if not argv or any(s.startswith(a) for a in argv)]
    for s in steps:
        t = time.time()
        print(f"=== {s}", flush=True)
        importlib.import_module(f"pipeline.{s}").main()
        print(f"=== {s} done in {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
