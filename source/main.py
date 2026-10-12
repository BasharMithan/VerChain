from core.verchain import Verchain



def main() -> None:
    verchain = Verchain("Blockchain", "localhost", 8000)
    verchain.start()



if __name__ == "__main__":
    main()