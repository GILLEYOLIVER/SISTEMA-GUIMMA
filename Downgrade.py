import sys

from sistema_atualizacao import downgrade_sistema


def main() -> int:
    try:
        log_path = downgrade_sistema()
        print(f"Downgrade concluído. Log: {log_path}")
        return 0
    except Exception as exc:
        print(f"Erro ao realizar downgrade: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
