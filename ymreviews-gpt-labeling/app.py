from parse import *
from labels import *

st.write("# Разметка отзывов на товары с Яндекс.Маркет с помощью GPT")

if 'data' not in st.session_state:
    st.session_state['data'] = {}

input_form = st.form(key='input_form')
st.session_state.MAX_REVIEWS_NUM = input_form.text_input(
        "Количество отзывов для разметки",
        value=20,
        key='max_reviews_num',
        disabled=False,
        placeholder="Введите максимальное количество отзывов для разметки"
    )
st.session_state.URL = input_form.text_input(
        "Ссылка на товар",
        key='url',
        disabled=False,
        placeholder="Введите ссылку на товар"
    ).split('?')[0]

input_submit_button = input_form.form_submit_button('Скачать отзывы')

URL = st.session_state.URL

# @st.cache_data
def label_data():
    pred_labels_zero_shot, responses_full_zero_shot = label_prediction(product_title, reviews_df['review'].values, PROPERTY)
    st.session_state.data[URL]['properties'][PROPERTY]['labels'] = {'zero-shot': pred_labels_zero_shot}
    st.session_state.data[URL]['properties'][PROPERTY]['responses'] = {'zero-shot': responses_full_zero_shot}
    time.sleep(5)

    pred_labels_cot, responses_full_cot = label_prediction(product_title, reviews_df['review'].values, PROPERTY, method='chain-of-thought')
    st.session_state.data[URL]['properties'][PROPERTY]['labels'].update({'chain-of-thoughts': pred_labels_cot})
    st.session_state.data[URL]['properties'][PROPERTY]['responses'].update({'chain-of-thoughts': responses_full_cot})
    time.sleep(5)

    pred_labels_reflection, responses_full_reflection = label_prediction(product_title, reviews_df['review'].values, PROPERTY, method='reflection',
                                                                        base_cot_responses=responses_full_cot)
    st.session_state.data[URL]['properties'][PROPERTY]['labels'].update({'reflection': pred_labels_reflection})
    st.session_state.data[URL]['properties'][PROPERTY]['responses'].update({'reflection': responses_full_reflection})

    labels_df = pd.DataFrame({
        'Zero-shot': pred_labels_zero_shot,
        'Chain of Thoughts': pred_labels_cot,
        'Self-Reflection': pred_labels_reflection 
    }, dtype='int64')
    labels = pd.concat([reviews_df, labels_df], axis=1).dropna(subset=['Zero-shot', 'Chain of Thoughts', 'Self-Reflection'])

    return labels, responses_full_zero_shot, responses_full_cot, responses_full_reflection

if URL not in st.session_state.data.keys():
    print("URL:", URL)
    if input_submit_button and not URL:
        warning = input_form.warning("Введите ссылку на товар!")
    elif input_submit_button:
        PRODUCT = {'url': URL + "/reviews?sort_by=date"}
        product_title, reviews = product_reviews_parse(PRODUCT)

        st.session_state.data[URL] = {
            'product_title': ''.join(product_title),
            'reviews': pd.DataFrame(reviews),
            'properties': None
        }

if URL in st.session_state.data.keys():
    product_title = st.session_state.data[URL]['product_title']
    reviews_df = st.session_state.data[URL]['reviews']

    with st.form(key='data_form'):
        st.write(f"### {product_title}")
        st.dataframe(reviews_df, height=min(35*(reviews_df.shape[0]+1)+2, 210))

        if st.session_state.data[URL]['properties'] is None:
            properties_response, _ = openai_chat_completion_request(product_property_prompt(product_title, reviews_df.sample(min(reviews_df.shape[0], 10)).review.values))
            properties_list = properties_response.split('\n')[-1].strip('][').split(', ')
            st.session_state.data[URL]['properties'] = {k: {} for k in properties_list}
            print('SUGGESTED PROPERTIES\n', st.session_state.data[URL]['properties'].keys())

        PROPERTY = st.selectbox(
            'Выберите свойство для анализа',
            ([p.strip('\'') for p in list(st.session_state.data[URL]['properties'].keys()) + ['Другое свойство']]),
        )
        if PROPERTY == 'Другое свойство':
            PROPERTY = st.text_input(
                "Введите свойство для анализа",
                disabled=False,
                placeholder="Введите свойство для анализа"
            )
            if PROPERTY:
                st.session_state.data[URL]['properties'].update({PROPERTY.capitalize(): {}})
        
        st.session_state.PROPERTY = PROPERTY
        
        data_submit_button = st.form_submit_button('Разметить отзывы')

    print("CHOSEN PROPERTY:", st.session_state.PROPERTY)

    if data_submit_button and st.session_state.PROPERTY:
        PROPERTY = st.session_state.PROPERTY.capitalize()
        st.write(f"## Разметка отзывов: {PROPERTY.lower()}")

        if not st.session_state.data[URL]['properties'][PROPERTY]:
            labels, responses_full_zero_shot, responses_full_cot, responses_full_reflection = label_data()
            st.session_state.data[URL]['labeled_reviews'] = labels
        
        elif set(st.session_state.data[URL]['properties'][PROPERTY]['labels'].keys()) == {'zero-shot', 'chain-of-thoughts', 'reflection'}:
            print("Reviews already labeled")
            labels = st.session_state.data[URL]['labeled_reviews']
            responses_full_zero_shot = st.session_state.data[URL]['properties'][PROPERTY]['responses']['zero-shot']
            responses_full_cot = st.session_state.data[URL]['properties'][PROPERTY]['responses']['chain-of-thoughts']
            responses_full_reflection = st.session_state.data[URL]['properties'][PROPERTY]['responses']['reflection']

        st.write("#### Размеченные данные")
        st.dataframe(labels)

        st.divider()
        st.write(f"## Анализ отзывов: {PROPERTY.lower()}")

        for i in range(labels.shape[0]):
            with st.container():
                st.divider()
                st.write(f"#### **{labels.reviewer.iloc[i]}**")
                st.write(int(labels.rating.iloc[i]) * "★" + (5 - int(labels.rating.iloc[i])) * "☆")
                st.write(labels.review.iloc[i])

                # column view
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Zero-shot Label**")
                    val = labels["Zero-shot"].iloc[i]
                    with st.expander(f"{val}"):
                        st.text(responses_full_zero_shot[i])                    
                with col2:
                    val = labels["Chain of Thoughts"].iloc[i]
                    st.write(f"**Chain of Thoughts Label**")
                    with st.expander(f"{val}"):
                        st.text(responses_full_cot[i])
                with col3:
                    val = labels["Self-Reflection"].iloc[i]
                    st.write(f"**Self-Reflection Label**")
                    with st.expander(f"{val}"):
                        st.text(responses_full_reflection[i])

                # row view
                # st.write(f"**Zero-shot Label**")
                # val = labels["Zero-shot"].iloc[i]
                # with st.expander(f"{val}"):
                #     st.text(responses_full_zero_shot[i])
                # st.write(f"**Chain of Thoughts Label**")
                # val = labels["Chain of Thoughts"].iloc[i]
                # with st.expander(f"{val}"):
                #     st.text(responses_full_cot[i])
                # st.write(f"**Self-Reflection Label**")
                # val = labels["Self-Reflection"].iloc[i]
                # with st.expander(f"{val}"):
                #     st.text(responses_full_reflection[i])
