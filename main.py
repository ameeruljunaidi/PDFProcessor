from PyPDF2 import PdfReader
import tkinter as tk
from tkinter import filedialog
import openai
import clipboard
import tiktoken
import time
from datetime import datetime

openai.api_key = "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"


def get_file():
    application_window = tk.Tk()
    my_filetypes = [('all files', '.*'), ('text files', '.txt')]

    answer = filedialog.askopenfilename(parent=application_window, initialdir="C:/Users/User/Downloads",
                                        title="Please select a file:", filetypes=my_filetypes)
    return answer


def get_text_from_file():
    file_path = get_file()
    reader = PdfReader(file_path)

    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return text


def count_cost(token_count):
    cost = token_count / 1000 * 0.002
    print(f"Cost is {print_cad(cost)}")
    return cost


def check_cost():
    split_text_into_tokens(get_text_from_file())


def print_cad(amount):
    return f"CAD ${round(amount * 1.36, 8)}"


# Returns list of texts split into chunks and token_count
def split_text_into_tokens(text):
    n = 4000

    print("Splitting text into tokens...")
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = encoding.encode(text)
    cost = count_cost(len(tokens))
    tokens_split = [tokens[x:x + n] for x in range(0, len(tokens), n)]

    total_file = open("total.txt", "r")
    total = float(total_file.read())
    total_file.close()

    total += cost
    print(f"Total cost so far would be: {print_cad(total)}")

    time_taken = round((len(tokens_split) / 3) * 72 / 60, 2)
    if len(tokens_split) > 3 and time_taken > 0:
        print(f"Will be sleeping for {time_taken} minutes")

    proceed = input("Proceed? (Y/N) ")

    if not proceed.lower().startswith("y"):
        exit(1)

    with open("total.txt", "w") as f:
        f.write(str(total))
        f.close()

    with open("log.txt", "a") as f:
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        f.write(f"{now}: ${cost}\n")

    tokens_decoded = [encoding.decode(x) for x in tokens_split]
    return tokens_decoded


def generate_prompt(text, prompt):
    return f"{prompt} {text}"


def get_response(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    return response


def ask_follow_up(messages):
    response = get_response(messages)

    print(f"A: {response.choices[0].message.content}")
    return [messages, response]


def summarize_single_tokens(text, prompt, messages):
    system_msg = "You are a financial analyst"
    user_msg = generate_prompt(text, prompt)

    if len(messages) == 0:
        messages.append({"role": "system", "content": system_msg})

    messages.append({"role": "user", "content": user_msg})

    print("Summarizing...")

    response = get_response(messages)

    return [messages, response]


def sleep():
    print("Sleeping...")
    time.sleep(72)


def summarize_multiple_tokens(texts, prompt, context=False):
    results = []
    messages = []

    for idx, text in enumerate(texts):
        if not context:
            messages = []

        [temp_messages, temp_response] = summarize_single_tokens(text, prompt, messages)
        content = temp_response.choices[0].message.content
        role = temp_response.choices[0].message.role

        results.append(content)

        if context:
            messages = [x.role != "user" for x in temp_messages]
            messages.append({"role": role, "content": content})

        if (idx + 1) % 3 == 0:
            sleep()

    combined = "\n".join(results)

    if (len(texts) + 1) % 3 == 0:
        sleep()

    summarizer = summarize_single_tokens(combined, prompt, messages)
    [updated_messages, response] = summarizer

    return [updated_messages, response]


def summarize_pdf(prompt="summarize in bullet points: ", context=False):
    [old_messages, result] = summarize_multiple_tokens(split_text_into_tokens(get_text_from_file()), prompt, context)
    result_content = result.choices[0].message.content
    print(result_content)
    clipboard.copy(result_content)

    now = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    file_name = f"archive/output_{now}.txt"
    with open(file_name, "w") as f:
        f.write(result_content)

    if not context:
        return result

    new_messages = {"role": result.choices[0].message.role, "content": result.choices[0].message.content}
    old_messages.append(new_messages)

    while True:
        follow_up = input("Q: ")

        if follow_up == "":
            break
        else:
            old_messages.append({"role": "user", "content": follow_up})
            [_, response] = ask_follow_up(old_messages)
            role = response.choices[0].message.role
            content = response.choices[0].message.content
            old_messages.append({"role": role, "content": content})

            with open(file_name, "a") as f:
                f.write(f"Q: {follow_up}\n")
                f.write(f"A: {content}\n")

    return result


def reset_logs():
    fa = open("log.txt", "w")
    fa.close()
    fb = open("total.txt", "w")
    fb.write("0")
    fb.close()


def generate_chunks():
    file_path = get_file()
    filename = file_path.split("/")[-1].split(".")[0]
    reader = PdfReader(file_path)

    count = 1
    text = ""
    for page in reader.pages:
        text += page.extract_text()
        max_page = 5
        if count % max_page == 0 or count == len(reader.pages):
            page_number = int(count / max_page) if count % max_page == 0 else int(count / max_page) + 1
            output_filename = f"{filename}_{page_number}"
            text += f"to be continued, this is part {page_number}" if count != len(
                reader.pages) else "this the end of the document"
            with open(f"C:/Users/User/Downloads/Chunks/{output_filename}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            text = ""
        count += 1


if __name__ == '__main__':
    summarize_pdf()
