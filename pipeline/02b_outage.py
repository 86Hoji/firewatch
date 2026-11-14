"""Pipeline step: satellite-wide S-NPP outage days from all countries (see pipeline/outage.py)."""
from pipeline import outage


def main():
    outage.main()


if __name__ == "__main__":
    main()
