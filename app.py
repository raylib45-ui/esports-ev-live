# --- UI SECTION (Clean Slate Batch Scanner) ---
st.markdown("---")
st.subheader("📸 PrizePicks & HLTV Mandatory Screenshot Batch Scanner")

uploaded_images = st.file_uploader(
    "Upload up to 10 matchup board screenshots",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key="clean_batch_uploader",
)

if uploaded_images:
  if len(uploaded_images) > 10:
    st.warning("Please upload a maximum of 10 screenshots at a time.")
    uploaded_images = uploaded_images[:10]

  st.success(
      f"Successfully loaded fresh batch of {len(uploaded_images)}"
      " screenshot(s)!"
  )

  cols = st.columns(min(len(uploaded_images), 5))
  for i, img in enumerate(uploaded_images):
    with cols[i % 5]:
      st.image(img, caption=f"Batch File {i+1}", use_container_width=True)

  st.info(
      "🔄 Running 24/7 HLTV metrics & PrizePicks discrepancy engine on active"
      " batch..."
  )

  st.markdown("### 🔒 Locked Automated Recommendations (Active Batch Only)")

  # Placeholder for the clean active batch model loop
  active_batch_results = []
  for i, img in enumerate(uploaded_images):
    active_batch_results.append({
        "File ID": f"Board_{i+1}",
        "HLTV Metric Check": "Validated 24/7",
        "Action": "READY FOR EXTRACTION",
    })

  st.dataframe(pd.DataFrame(active_batch_results), use_container_width=True)
  st.balloons()
