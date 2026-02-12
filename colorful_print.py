from colorama import init, Style, Back

init(autoreset=True)


def ptbk(text):
    print(f"{Back.BLACK}{text}{Style.RESET_ALL}")


def ptrd(text):
    print(f"{Back.RED}{text}{Style.RESET_ALL}")


def ptgn(text):
    print(f"{Back.GREEN}{text}{Style.RESET_ALL}")


def ptyw(text):
    print(f"{Back.YELLOW}{text}{Style.RESET_ALL}")


def ptbe(text):
    print(f"{Back.BLUE}{text}{Style.RESET_ALL}")


def ptmga(text):
    print(f"{Back.MAGENTA}{text}{Style.RESET_ALL}")


def ptcn(text):
    print(f"{Back.CYAN}{text}{Style.RESET_ALL}")


def ptwe(text):
    print(f"{Back.WHITE}{text}{Style.RESET_ALL}")
