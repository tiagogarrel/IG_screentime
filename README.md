# Screen Time Tracker

This is a small personal project built with **Streamlit** and **Google Sheets** to track daily screen time and analyze habits over time.

The idea was simple. I wanted an easy way to log my screen time day by day, visualize patterns, and spot bad streaks without using heavy tools or paid apps.

---

## What it does

- Log daily screen time manually  
- One-click button to save today’s screen time  
- Use Google Sheets as a lightweight database  
- Analyze a selected date range (default is the last 7 days)  
- Show key metrics:
  - Average minutes per day  
  - Days above and below a daily goal  
  - Missing days  
  - Current streak under a threshold  
- Visualizations:
  - Daily line chart  
  - Weekday heatmap (green to red, soft colors)  
  - Table highlighting missing days  

---

## How it works

- The app connects to a Google Sheet using a service account  
- Each day is stored as a row with date, minutes, source, and timestamp  
- Missing days are inferred when building the selected date range  
- The heatmap aggregates average screen time by weekday  
- All analytics update automatically when the data changes  

---

## Tech stack

- Python  
- Streamlit  
- Pandas  
- Google Sheets API (via gspread)  
- Matplotlib (for heatmap styling)  

Google Sheets is used as the backend on purpose. It’s simple, transparent, and easy to inspect or edit manually if needed.

---

## Project structure

.
├── app.py # Streamlit app
├── sheets.py # Google Sheets logic
├── requirements.txt
├── README.md

Secrets and credentials are handled via Streamlit Cloud secrets and are not part of the repo.

---

