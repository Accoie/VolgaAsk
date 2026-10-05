import sys

from converter import PdfConvertError, PdfConverter
from configs.config import ConverterConfig


def main() -> int:
    config = ConverterConfig()
    converter = PdfConverter(
        input_dir=config.input_dir,
        output_dir=config.output_dir,
    )

    try:
        converter.convert_all()
    except PdfConvertError as error:
        print(f"[FATAL] {error}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())