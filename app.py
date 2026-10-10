
import streamlit as st
import requests
import pandas as pd
from io import StringIO

API = "http://localhost:8080/api/v1/jobs"

st.set_page_config(page_title="LeadPilot AI", layout="wide")
st.title("LeadPilot AI")
st.write("Find real businesses for your service.")

service = st.text_input("What service do you offer?")
target = st.text_input("Which businesses are your target clients?")

# Start a real Google Maps scraping job
if st.button("Find Leads"):
    if not service.strip() or not target.strip():
        st.error("Please fill in both fields.")
    else:
        payload = {
            "name": "LeadPilot Search",
            "keywords": [target.strip()],
            "lang": "en",
            "zoom": 13,
            "lat": "17.3850",
            "lon": "78.4867",
            "fast_mode": True,
            "radius": 5000,
            "depth": 5,
            "email": False,
            "max_time": 120
        }

        try:
            with st.spinner("Starting Google Maps search..."):
                response = requests.post(
                    API,
                    json=payload,
                    timeout=20
                )
                response.raise_for_status()

                job_id = response.json()["id"]

            st.session_state["job_id"] = job_id
            st.session_state["service"] = service.strip()
            st.session_state["target"] = target.strip()
            st.session_state.pop("leads_df", None)
            st.session_state.pop("leads_csv", None)

            # Clear previous results when starting a new search
            st.session_state.pop("leads_df", None)
            st.session_state.pop("leads_csv", None)

            st.success(f"Search job created: {job_id}")
            st.info(
                "Wait for the scraper to finish, then click "
                "'Download Results'."
            )

        except requests.RequestException as e:
            st.error(f"Could not connect to the scraper: {e}")
        except (ValueError, KeyError) as e:
            st.error(f"Unexpected response from the scraper: {e}")

# Download real scraper results
if st.session_state.get("job_id"):
    st.subheader("Search Results")

    if st.button("Download Results"):
        try:
            job_id = st.session_state["job_id"]

            with st.spinner("Loading scraper results..."):
                result = requests.get(
                    f"{API}/{job_id}/download",
                    timeout=30
                )
                result.raise_for_status()

                csv_text = result.content.decode(
                    "utf-8-sig",
                    errors="replace"
                ).strip()

            if not csv_text:
                st.warning(
                    "The scraper returned an empty response. "
                    "Wait a little and try downloading again."
                )
            else:
                try:
                    df = pd.read_csv(StringIO(csv_text))
                except pd.errors.EmptyDataError:
                    st.warning(
                        "No CSV data is available yet. "
                        "Wait and try again."
                    )
                    df = None

                if df is not None:
                    if df.empty:
                        st.warning(
                            "The search returned no business records."
                        )
                    else:
                        # Save the successfully downloaded results
                        st.session_state["leads_df"] = df
                        st.session_state["leads_csv"] = result.content

        except requests.RequestException as e:
            st.error(
                f"Could not download results from the backend: {e}"
            )
        except Exception as e:
            st.error(f"Could not process the results: {e}")

    # Display results after download, including after Streamlit reruns
    df = st.session_state.get("leads_df")

    if df is not None:
        st.success(f"Found {len(df)} business records.")
        st.dataframe(df, width="stretch")

        st.download_button(
            "Save CSV",
            data=st.session_state["leads_csv"],
            file_name="leads.csv",
            mime="text/csv"
        )

        st.subheader("Business Opportunity Analysis")
        st.caption(
            "Rule-based suggestions using available public data. "
            "These are hypotheses, not verified business needs "
            "or AI-generated conclusions."
        )

        if "title" not in df.columns:
            st.warning(
                "The scraper results do not contain a 'title' column. "
                "Available columns: " + ", ".join(map(str, df.columns))
            )
        else:
            service_text = st.session_state.get("service", "").strip()

            for index, (_, lead) in enumerate(df.head(5).iterrows()):
                business_name = str(lead.get("title", "")).strip()

                if not business_name or business_name.lower() == "nan":
                    business_name = "Business"

                website = lead.get("website")
                rating = lead.get("review_rating")
                reviews = lead.get("review_count")

                st.markdown(f"### {business_name}")

                if pd.notna(website) and str(website).strip():
                    st.write("Website:", str(website))
                else:
                    st.write("Website: Not listed in scraper results")

                st.write(
                    "Rating:",
                    rating if pd.notna(rating) else "Not available"
                )
                st.write(
                    "Reviews:",
                    reviews if pd.notna(reviews) else "Not available"
                )

                # Rule-based opportunity hypothesis
                st.markdown("**Opportunity analysis**")
                st.write(f"Service offered: {service_text}")

                try:
                    rating_num = (
                        float(rating) if pd.notna(rating) else None
                    )
                    reviews_num = (
                        int(float(reviews))
                        if pd.notna(reviews) else None
                    )
                except (ValueError, TypeError):
                    rating_num = None
                    reviews_num = None

                if (
                    rating_num is not None
                    and reviews_num is not None
                ):
                    if rating_num < 4.0 and reviews_num >= 10:
                        opportunity = (
                            "Explore whether customer feedback analysis "
                            "could help this business. A lower rating "
                            "does not establish the cause of the rating."
                        )
                    elif reviews_num >= 50:
                        opportunity = (
                            "Explore whether review monitoring and "
                            "response workflows could be useful given "
                            "the volume of public reviews."
                        )
                    else:
                        opportunity = (
                            "Assess whether review analysis or response "
                            "automation could provide value."
                        )

                    st.write(
                        f"Public evidence: {rating_num}/5 from "
                        f"{reviews_num} reviews."
                    )
                else:
                    opportunity = (
                        "Research this business further before proposing "
                        "a service. The available data is insufficient "
                        "to identify a specific need."
                    )

                st.info(f"Potential opportunity: {opportunity}")

                # Editable outreach draft; nothing is sent automatically
                st.markdown("**Suggested outreach draft**")

                email_draft = f"""Subject: An idea for {business_name}

Hi {business_name} team,

I offer {service_text}.

I came across your business while researching local businesses
and thought this service might be worth exploring for your team.

If this is relevant to your business, I'd be happy to discuss
a practical approach.

Would this be useful to your team?

If you do not wish to receive further messages, please let me know.

Best,
LeadPilot AI user
"""

                st.text_area(
                    "Review and edit before sending",
                    value=email_draft,
                    height=220,
                    key=f"draft_{index}_{st.session_state['job_id']}"
                )	