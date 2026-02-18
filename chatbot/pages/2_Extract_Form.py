"""
Extract Form Page — Upload ACORD PDF and extract fields.
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="Extract Form - Insurance Bot", page_icon="📄", layout="wide")
st.title("ACORD Form Extraction")

st.markdown("""
Upload an ACORD PDF form (125, 127, or 137) to extract structured field data.
The extraction uses the OCR + LLM pipeline with optional VLM support.
""")

# ── Upload ──
uploaded_file = st.file_uploader("Upload ACORD PDF", type=["pdf"])

if uploaded_file:
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp.name)

    st.success(f"Uploaded: {uploaded_file.name}")

    # Form type detection
    col1, col2 = st.columns(2)
    with col1:
        form_type = st.selectbox("Form type", ["auto-detect", "125", "127", "137"])
    with col2:
        use_gpu = st.checkbox("Use GPU", value=True)

    if st.button("Extract Fields", type="primary"):
        with st.spinner("Extracting fields... This may take a few minutes."):
            try:
                from extractor import ACORDExtractor

                extractor = ACORDExtractor(
                    form_type=form_type if form_type != "auto-detect" else None,
                    use_gpu=use_gpu,
                )

                output_dir = tmp_path.parent / f"extract_{tmp_path.stem}"
                output_dir.mkdir(exist_ok=True)

                result = extractor.extract(tmp_path, output_dir)

                if result:
                    st.success(f"Extracted {len(result)} fields")

                    # Display as table
                    st.subheader("Extracted Fields")
                    table_data = []
                    for field_name, value in sorted(result.items()):
                        if value is not None and str(value).strip():
                            table_data.append({
                                "Field": field_name,
                                "Value": str(value),
                            })
                    st.dataframe(table_data, use_container_width=True)

                    # Download as JSON
                    json_str = json.dumps(result, indent=2, ensure_ascii=False)
                    st.download_button(
                        "Download JSON",
                        data=json_str,
                        file_name=f"{uploaded_file.name.replace('.pdf', '')}_extracted.json",
                        mime="application/json",
                    )
                else:
                    st.warning("No fields extracted. Check if the PDF is a valid ACORD form.")
            except Exception as e:
                st.error(f"Extraction failed: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("**ACORD Insurance Bot** v1.0")
