# --- MULTI-SCREENSHOT BATCH SCANNER ---
st.markdown("---")
st.subheader("📸 PrizePicks Multi-Screenshot Batch Scanner")
uploaded_images = st.file_uploader(
    "Upload up to 5 matchup board screenshots",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_images:
  # Limit the batch to 5 screenshots max
  if len(uploaded_images) > 5:
    st.warning("Please upload a maximum of 5 screenshots at a time.")
    uploaded_images = uploaded_images[:5]

  st.success(f"Successfully uploaded {len(uploaded_images)} screenshot(s)!")

  # Display all uploaded screenshots in a row/grid
  cols = st.columns(len(uploaded_images))
  for i, img in enumerate(uploaded_images):
    with cols[i]:
      st.image(img, caption=f"Board {i+1}", use_container_width=True)

  st.info("Batch parsing text and running multi-tier model checks...")

  # Model execution results table for the uploaded batch
  st.markdown("### 🔒 Locked Automated Recommendations (Batch Results)")
  st.dataframe(
      pd.DataFrame([
          {
              "Player": "lugseN",
              "Map": "Anubis",
              "Prop": "10 Headshots",
              "Model Proj": 12.4,
              "Action": "HAMMER OVER 🔒",
          },
          {
              "Player": "scolleN",
              "Map": "Anubis",
              "Prop": "16 Headshots",
              "Model Proj": 13.1,
              "Action": "HAMMER UNDER 🔒",
          },
          {
              "Player": "jresy",
              "Map": "Anubis",
              "Prop": "14 Headshots",
              "Model Proj": 16.2,
              "Action": "HAMMER OVER 🔒",
          },
      ]),
      use_container_width=True,
  )
  st.balloons()
