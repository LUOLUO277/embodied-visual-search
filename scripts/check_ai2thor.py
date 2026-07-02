from __future__ import annotations


def main() -> None:
    try:
        import ai2thor  # noqa: F401

        print("ai2thor import ok")
    except Exception as exc:
        print(f"ai2thor import failed: {exc}")
        raise


if __name__ == "__main__":
    main()
