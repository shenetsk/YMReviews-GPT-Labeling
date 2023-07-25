from parse import *
from labels import *

st.write("# Разметка отзывов на товары с Яндекс.Маркет с помощью GPT")

input_form = st.form(key='input_form')
MAX_REVIEWS_NUM = input_form.text_input(
        "Количество отзывов для разметки",
        value=20,
        key='max_reviews_num',
        disabled=False,
        placeholder="Введите максимальное количество отзывов для разметки"
    )
URL = input_form.text_input(
        "Ссылка на товар",
        key='url',
        disabled=False,
        placeholder="Введите ссылку на товар"
    )

input_submit_button = input_form.form_submit_button('Скачать отзывы')

if 'reviews_df' not in st.session_state:
    if input_submit_button and not URL:
        warning = input_form.warning("Введите ссылку на товар!")
    elif input_submit_button:
        PRODUCTS = [{'url': URL.split('?')[0] + "/reviews?sort_by=date"}]
        st.session_state.product_title, reviews = product_reviews_parse(PRODUCTS)
        st.session_state.reviews_df = pd.DataFrame(reviews)

        # #
        # df = pd.read_excel('../../data/reviews.xlsx').sample(int(MAX_REVIEWS_NUM))
        # df = df.fillna(0)
        # df['label'] = df['label'].astype(int)
        # st.session_state.reviews_df = df
        # st.session_state.product_title = 'Принтер с термопечатью Xiaomi Mijia AR ZINK, цветн., меньше A6, белый'
        # #

if 'reviews_df' in st.session_state:
    reviews_df = st.session_state.reviews_df
    product_title = st.session_state.product_title
    with st.form(key='data_form'):
        st.write(f"### {''.join(product_title)}")
        st.dataframe(reviews_df, height=min(35*(reviews_df.shape[0]+1)+2, 210))

        if 'properties' not in st.session_state:
            properties_response, _ = openai_chat_completion_request(product_property_prompt(product_title))
            st.session_state.properties = properties_response.split('\n')[-1].strip('][').split(', ')
            print(st.session_state.properties)

        st.session_state.PROPERTY = st.selectbox(
            'Выберите свойство для анализа',
            ([p.strip('\'') for p in st.session_state.properties] + ['Другое свойство']),
        )
        
        if st.session_state.PROPERTY == 'Другое свойство':
            st.session_state.PROPERTY = st.text_input(
                "Введите свойство для анализа",
                disabled=False,
                placeholder="Введите свойство для анализа"
            )

        data_submit_button = st.form_submit_button('Разметить отзывы')

    PROPERTY = st.session_state.PROPERTY
    print(st.session_state.PROPERTY)

    if PROPERTY and data_submit_button:
        st.write(f"## Разметка: {PROPERTY.lower()}")
        pred_labels_zero_shot, responses_full_zero_shot = label_prediction(product_title, reviews_df['review'].values, PROPERTY)
        time.sleep(5)
        pred_labels_cot, responses_full_cot = label_prediction(product_title, reviews_df['review'].values, PROPERTY, method='chain-of-thought')
        time.sleep(5)
        pred_labels_reflection, responses_full_reflection = label_prediction(product_title, reviews_df['review'].values, PROPERTY, method='reflection')

        labels = reviews_df.copy()
        labels['Zero-shot'] = pred_labels_zero_shot
        labels['CoT'] = pred_labels_cot
        labels['Self-Reflection'] = pred_labels_reflection

        st.write("#### Размеченные данные")
        st.dataframe(labels)

        st.divider()
        st.write(f"## Анализ отзывов: {PROPERTY.lower()}")

        for i in range(labels.shape[0]):
            with st.container():
                st.divider()
                st.write(f"#### **{labels.reviewer.iloc[i]}**")
                st.write(labels.review.iloc[i])

                # col1, col2, col3 = st.columns(3)
                # with col1:
                #     st.write(f"**Zero-shot Label**")
                #     val = labels["Zero-shot"].iloc[i]
                #     with st.expander(f"{val}"):
                #         st.code(responses_full_zero_shot[i])

                #     c1, c2 = st.columns(2)
                #     with c1:
                #         st.code(f"{val}")
                #     with c2:
                #         if st.button("Ответ"):
                #             output.code(responses_full_zero_shot[i])
                    
                # with col2:
                #     val = labels["CoT"].iloc[i]
                #     st.write(f"**Chain of Thoughts Label**")
                #     with st.expander(f"{val}"):
                #         st.code(responses_full_cot[i])
                # with col3:
                #     val = labels["Self-Reflection"].iloc[i]
                #     st.write(f"**Self-Reflection Label**")
                #     with st.expander(f"{val}"):
                #         st.code(responses_full_reflection[i])

                # output = st.container()

                
            st.write(f"**Zero-shot Label**")
            val = labels["Zero-shot"].iloc[i]
            with st.expander(f"{val}"):
                st.text(responses_full_zero_shot[i])
            
            val = labels["CoT"].iloc[i]
            st.write(f"**Chain of Thoughts Label**")
            with st.expander(f"{val}"):
                st.text(responses_full_cot[i])
            val = labels["Self-Reflection"].iloc[i]
            st.write(f"**Self-Reflection Label**")
            with st.expander(f"{val}"):
                st.text(responses_full_reflection[i])
