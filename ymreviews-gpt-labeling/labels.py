import json
import openai
import time
import os
import pandas as pd
import streamlit as st

MODEL = "gpt-3.5-turbo"

def openai_key_load():
    environ_key = "OPENAI_API_KEY"
    if environ_key not in os.environ:
        path = os.path.join(os.path.expanduser("~"), ".openai", "key.txt")
        try:
            with open(path, "r") as f:
                openai_key = f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"OpenAI key file not found at {path}")
        os.environ[environ_key] = openai_key

    return os.environ[environ_key]

def openai_pricing_get(model_name):
    price_file = os.path.join(os.path.dirname(__file__), "pricing.json")
    with open(price_file, "r") as f:
        prices = json.load(f)

    if model_name not in prices:
        raise ValueError(f"Model '{model_name}' not found in price list")

    return prices[model_name]

def calculate_cost(chat_completion, model_name):
    input_price, output_price = openai_pricing_get(model_name)
    return (chat_completion.usage["prompt_tokens"] * input_price + chat_completion.usage["completion_tokens"] * output_price) / 1000

def openai_chat_completion_request(prompt):
    openai.api_key = openai_key_load()

    chat_completion = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    request_cost = calculate_cost(chat_completion, MODEL)
    return chat_completion.choices[0].message.content, request_cost

def product_property_prompt(product_name, reviews):
    prompt = (
        f"I parsed a marketplace page of the following product: {product_name}\n"
        f"Here are some reviews to the product:\n"
        f"{reviews}\n\n"
        f"Your task is to define several possible subjective performance characteristics which can be used to describe the product.\n"
        f"EXAMPLE:\n"
        f"Product: Принтер с термопечатью Xiaomi Mijia AR ZINK, цветн., меньше A6, белый\n"
        f"Output:\n[Качество печати, Быстрота печати, Скорость сканирования]"
        f"The result should be defined by the product category as well as characteristics from the reviews.\n"
        f"Provide output on a separate line as python list, containing chosen properties."
    )
    return prompt

def review_label_prompt(review_text, product_name, property):
    prompt = (
        f"I parsed a marketplace page of the following product: {product_name} and got the following product review:\n"
        f"{review_text}\n\n"
        f"Your task is to decide whether it is possible to make direct conclusions about the {property} of the product from this review.\n"
        f"Please label this review with a binary flag, which is equal to 1 if it is possible to make conclusions about the {property} of the product from this review, and 0 otherwise.\n"
        f"Provide output as the only binary value."
    )
    return prompt

def chain_of_thought_review_label_prompt(review_text, product_name, property):
    prompt = (
        f"QUESTION:\n"
        f"I parsed a marketplace page of the following product: {product_name} and got the following product review:\n"
        f"{review_text}\n\n"
        f"Generate a step-by-step chain of thoughts about whether this review contains concrete information about the {property} of the product \
            and define if it is possible to make direct conclusions about the {property} of the product from this review.\n"
        
        f"GUIDELINES:\n"
        f"Reviews generally contain three main sections: pros, cons and comments.\n"
        f"Extract all review points, concerning the product.\n"
        f"Pay attention to the section in which each review point is located.\n"
        f"The review is considered to contain concrete information of {property} only if \
            (1) it explicitly characterizes the {property}, \
            (2) it mentions the direct consequences of the product having good or bad {property} \
            (3) it contains user's implicit opinion on the {property}\n"
        f"Don't use indirect indications of {property}. Only use explicit and direct mentions of {property}.\n"

        f"OUTPUT:"
        f"Based on your reasoning please label this review with a binary flag, \
            which is equal to 1 if this review contains concrete information about {property} of the product, \
            and 0 otherwise.\n"
        f"Finish your output with separate line containing single resulting integer value without accompanying text or labels \
            using this template: 'Label:\\n0' or 'Label:\\n1'"
    )
    return prompt

def reflection_label_prompt(review_text, product_name, property, base_cot_response=None):
    base_cot_prompt = chain_of_thought_review_label_prompt(review_text, product_name, property)
    if not base_cot_response:
        base_cot_response = openai_chat_completion_request(base_cot_prompt)[0]
    
    reflection_prompt = (
        f"You are an advanced reasoning agent that can improve based on self reflection. "
        f"You will be given a previous reasoning trial in which you were given a question to answer. "
        f"Your task is to evaluate if the provided answer is correct and whether its reasoning follows the GUIDELINES.\n\n"
        f"Here is the first reasoning trial for you to analyse:\n"
        f"QUESTION: {base_cot_prompt}\n"
        f"ANSWER: {base_cot_response}\n\n"
        f"After completing the analysis, if the provided answer is incorrect, improve the reasoning to make final step-by-step decision about the label value.\n"
        f"Based on the corrected reasoning please label this review with a binary flag, \
            which is equal to 1 if this review contains concrete information about {property} of the product, \
            and 0 otherwise.\n"
        f"Finish your output with separate line containing single resulting integer value without accompanying text or labels \
            using this template: 'Label:\\n0' or 'Label:\\n1'\n\n"
    )
    return reflection_prompt

def label_prediction(product_name, reviews, property, method='zero-shot', base_cot_responses=None):
    request_cost = 0
    pred_labels = []
    reasonings = []

    prompt_options = {'zero-shot': [review_label_prompt, 'Zero-shot'],
                      'chain-of-thought': [chain_of_thought_review_label_prompt, 'Chain of Thoughts'],
                      'reflection': [reflection_label_prompt, 'Self-Reflection']}
    label_prompt = prompt_options[method][0]

    st.write(f"#### {prompt_options[method][1]}")
    percent_complete = 0
    progress_bar = st.progress(percent_complete, text=f"{int(percent_complete / len(reviews) * 100)}%")

    for idx, review_text in enumerate(reviews):
        if method == 'reflection' and base_cot_responses:
            cot_response = base_cot_responses[idx]
            prompt = label_prompt(review_text, product_name, property, base_cot_response=cot_response)
        else:
            prompt = label_prompt(review_text, product_name, property)

        try:
            response_text, inter_request_cost = openai_chat_completion_request(prompt)
        except:
            iter = 0
            while iter < 3:
                try: 
                    time.sleep(2)
                    response_text, inter_request_cost = openai_chat_completion_request(prompt)
                    break
                except:
                    iter += 1
            response_text, inter_request_cost = '', 0

        reasonings.append(response_text)
        try:
            response_label = int(response_text.strip('.\n\'')[-1])
        except:
            response_label = None
        pred_labels.append(response_label)

        request_cost += inter_request_cost
        
        percent_complete += 1
        progress_bar.progress(percent_complete / len(reviews), text=f"{int(percent_complete / len(reviews) * 100)}%")
    
    print(f"\nMETHOD: {prompt_options[method][1]}")
    print(f"=== Total request cost: ${request_cost}")
    print("=== Number of reviews labeled:", len(pred_labels))

    return pred_labels, reasonings