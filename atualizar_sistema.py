import sys

from sistema_atualizacao import atualizar_sistema


def main() -> int:
    try:
        log_path = atualizar_sistema()
        print(f"Atualização concluída. Log: {log_path}")
        return 0
    except Exception as exc:
        print(f"Erro ao atualizar o sistema: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
