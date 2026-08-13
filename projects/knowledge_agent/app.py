# projects/Knowledge_agent/app.py
import streamlit as st
import requests

API_ENDPOINT = "http://127.0.0.1:8000/knowledge/query"

st.set_page_config(page_title="Enterprise knowledge Hub", layout="wide")
st.title("Enterprise Knowledge Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask a question about internal documentation..."):
    # Append user prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Dispatch API Call
    with st.spinner("Retrieving facts..."):
        try:
            res = requests.post(API_ENDPOINT, json={"prompt": prompt, "top_k": 3}, timeout=30.0)  
            res.raise_for_status()
            data = res.json()

            answer = data["answer"]
            sources = data.get("sources", []) 
            confidence = data.get("confidence", "low")

        except requests.RequestException as e:
            answer = f"Error communicating with backend: {e}"
            sources, confidence = "low", "error"
            

    # Append assistant response
    with st.chat_message("assistant"):
        st.write(answer)

        # 1. Display Confidence Visual Badge
        if confidence == "high":
            st.caption("🟢 **Confidence:** High")
        elif confidence == "medium":
            st.caption("🟡 **Confidence:** Medium")
        else:
            st.caption("🔴 **Confidence:** Low / Unverified")

        if sources:
            with st.expander("Cited Sources"):
                for idx, src in enumerate(sources, 1):
                    page = src.get('page')
                    page_display = f"Page {page}" if page and page > 0 else "Full document"
                    st.markdown(f"**{idx}. {src.get('document')}** ({page_display})")
                    section = src.get('section', '')
                    section_display = f"Section: {section} | " if section and section not in ['', 'Novatech Enterprises'] else ""
                    st.caption(f"{section_display}Relevance: {src.get('relevance_score', 0):.2f}")
           

    st.session_state.messages.append({"role": "assistant", "content": answer})              

                   

