import contextlib
import getpass
import io
import os
import platform
import subprocess
import sys
from colorama import Fore, Style
from openai import OpenAI

def print_formatted(text: str, color: str = Fore.WHITE):
    print(f"{Style.RESET_ALL}{color}{text}{Style.RESET_ALL}")


def extract_code(text: str):
    code = text.split("```")[1] if "```" in text else text.strip("`")
    code = code.strip()
    if code.startswith("python"):
        code = code[6:]
    return code.strip()


def run_code(code: str):
    print_formatted("Running code:", Fore.YELLOW)
    print_formatted(code, Fore.CYAN)
    try:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(code, globals())
        return True, output.getvalue()
    except Exception as e:
        return False, f"Error: {type(e).__name__}: {str(e)}"


def install_package(package_name: str):
    print_formatted(f"Installing {package_name}...", Fore.YELLOW)
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def run_shell():
    openai_client = OpenAI()
    memory = [
        {
            "role": "system",
            "content": str(
                {
                    "environment": {
                        "username": getpass.getuser(),
                        "os": platform.system(),
                        "python_version": platform.python_version(),
                    },
                    "task": f"""Please write a full Python script for the user to accomplish their goal. 
The script will be immediately run, so it should be ready to work without any modifications,
Do not return any text that is not Python code.
Import all needed requirements at the top of the script.
Always use tqdm to show progress for any loops.
Return the full code in ``` blocks.
Print the final result if appropriate.
When faced with errors, give the full entire corrected script.
Never give explanations.""",
                }
            ),
        },
    ]

    while True:
        user_input = input(f"{os.getcwd()} {Fore.CYAN}engshell>{Style.RESET_ALL} ")

        if user_input.lower() in {"clear", "cls"}:
            os.system("cls" if platform.system() == "Windows" else "clear")
            memory = memory[:1]
            continue

        memory.append(
            {
                "role": "user",
                "content": str({"goal": user_input, "cwd": os.getcwd()}),
            }
        )

        while True:
            response = openai_client.chat.completions.create(
                model="gpt-4.1-mini", messages=memory # type: ignore
            )
            if not response.choices[0].message.content:
                print_formatted("LLM did not return any content. Retrying...", Fore.YELLOW)
                continue
            try:
                code = extract_code(response.choices[0].message.content)
            except Exception as e:
                print(f"Error ({e}): LLM response: {response}")
                exit()
            memory.append({"role": "assistant", "content": code})

            success, output = run_code(code)

            if success:
                print_formatted(output or "Code executed successfully.", Fore.GREEN)
                break
            elif "ModuleNotFoundError: No module named" in output:
                package_name = output.split("'")[-2]
                if (
                    input(
                        f"{Fore.YELLOW}Install {package_name} package? [y/N]: {Style.RESET_ALL}"
                    ).lower()
                    == "y"
                ):
                    install_package(package_name)
            else:
                print_formatted(output, Fore.RED)
                memory.append({"role": "system", "content": str({"error": output})})

        memory.append({"role": "system", "content": output})


if __name__ == "__main__":
    if os.name == "nt":
        os.system("")
    run_shell()
