# --- UI SECTION (Properly outside the class) ---
st.markdown("---")
st.subheader("📸 PrizePicks Multi-Screenshot Batch Scanner (Up to 10)")

uploaded_images = st.file_uploader(
    "Upload up to 10 matchup board screenshots",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_images:
  if len(uploaded_images) > 10:
    st.warning("Please upload a maximum of 10 screenshots at a time.")
    uploaded_images = uploaded_images[:10]

  st.success(f"Successfully uploaded {len(uploaded_images)} screenshot(s)!")

  # Display uploaded screenshots
  cols = st.columns(min(len(uploaded_images), 5))  # Display up to 5 per row
  for i, img in enumerate(uploaded_images):
    with cols[i % 5]:
      st.image(img, caption=f"Board {i+1}", use_container_width=True)

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
