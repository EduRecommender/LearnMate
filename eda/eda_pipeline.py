import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

import os
os.system("pip install seaborn==0.13.2")

import seaborn as sns


# Streamlit Page Configuration
st.set_page_config(page_title="Kaggle Courses EDA", layout="wide")

st.title("📊 Kaggle Dataset Exploratory Data Analysis")

# Load the dataset
@st.cache_data
def load_data():
    df = pd.read_csv("../input_data/kaggle_filtered_courses.csv")
    return df

kaggle_df = load_data()


# Drop the description column for better viewing
kaggle_temp = kaggle_df.drop(columns=["Course Description"])


#### DataFrame Basics

# Show basic statistics
st.subheader("📈 Dataset Overview")
st.write(kaggle_df.describe())

st.subheader("📊 Data shape")
st.write(kaggle_df.shape)



#### Data Overview

# Show dataframe with full width
st.subheader("🔍 Full Data Table (Head = 5)")
with st.expander("View Dataframe"):
    st.dataframe(kaggle_temp.head(5), use_container_width=True)


#### University Course Selection

# Sidebar Filters
st.sidebar.header("🔎 Filter Data")
unique_universities = kaggle_df["University"].unique()
selected_university = st.sidebar.selectbox("Select University", ["All"] + list(unique_universities))

if selected_university != "All":
    kaggle_df = kaggle_df[kaggle_df["University"] == selected_university]


# Show updated dataframe after filtering
st.subheader("🔍 Course Specific Data Table")
with st.expander("View Dataframe"):
    st.dataframe(kaggle_df, use_container_width=True)

#### University and Course Count

# University and Category Count occurrences
category_counts = kaggle_df.groupby(["University", "Category"]).size().reset_index(name="Course Count")

# Interactive Plotly Chart: University vs. Category
st.subheader("📉 University vs. Course Category: Expand graph for full visualization")

fig = px.bar(category_counts, 
             x="University", 
             y="Course Count", 
             color="Category", 
             text="Course Count",
             title="Number of Courses Offered per University by Category",
             barmode="stack")  # Stacked bars to show category distribution

st.plotly_chart(fig)


#### Available Courses within Dataset

# Value Counts for Course Categories
st.subheader("📚 Course Category Breakdown")
category_counts = kaggle_df["Category"].value_counts()
fig, ax = plt.subplots(figsize=(8, 4))
sns.barplot(x=category_counts.index, y=category_counts.values, palette="viridis", ax=ax)
plt.xticks(rotation=45)
st.pyplot(fig)



# Download Processed Data
st.subheader("📥 Download Processed Data")
csv = kaggle_df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv, file_name="filtered_kaggle_courses.csv", mime="text/csv")

st.success("✔️ Interactive EDA Complete! You can filter, analyze, and download the data.")


