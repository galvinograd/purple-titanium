"""Helper file for testing signature consistency across processes."""

import os

import purple_titanium as pt


@pt.task()
def process(
    data: list[int],
    options: dict[str, int | str],
    flags: set[bool],
    coords: tuple[float, float],
    nullable: str | None,
    mixed: int | str | list[float]
) -> list[int]:
    return data


def main() -> None:
    """Run the task and print its signature."""
    # Use different parameters if TEST_DIFFERENT_PARAMS is set
    if os.environ.get('TEST_DIFFERENT_PARAMS') == '1':
        task = process(
            data=[1, 2, 3],
            options={'size': 20, 'mode': 'fast'},  # Different size
            flags={True, False},
            coords=(1.5, 2.5),
            nullable=None,
            mixed=[1.0, 2.0]
        )
    else:
        task = process(
            data=[1, 2, 3],
            options={'size': 10, 'mode': 'fast'},
            flags={True, False},
            coords=(1.5, 2.5),
            nullable=None,
            mixed=[1.0, 2.0]
        )
    print(task.owner.signature)  # noqa: T201


if __name__ == '__main__':
    main()