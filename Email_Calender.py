from llama_index.llms.openrouter import OpenRouter
import ast
import json
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_community import GmailToolkit
from langchain.agents import AgentType,initialize_agent
from langchain.tools import Tool
from langchain_groq import ChatGroq
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
SCOPES = ["https://www.googleapis.com/auth/calendar","https://mail.google.com/"]
def Format(input):
    llm = OpenRouter(
            api_key="",
            model="openai/gpt-4o-2024-11-20",
            )
    
    prompt = f"""
    You are a JSON formatting expert. Your task is to fill the following JSON structure based on the user input.

    Example JSON structure:
    {{
        "summary": "Sample Event",
        "location": "Virtual",
        "description": "This is a test event.",
        "start": {{
            "dateTime": "2024-12-20T10:00:00",
            "timeZone": "America/Los_Angeles"
        }},
        "end": {{
            "dateTime": "2024-12-20T11:00:00",
            "timeZone": "America/Los_Angeles"
        }},
        "attendees": [
            {{"email": "example@example.com"}}
        ],
        "reminders": {{
            "useDefault": true
        }}
    }}

    USERINPUT: {input}

    Fill in the JSON structure with the information provided in the USERINPUT. Only provide the filled JSON without any explanation or additional text.
    """
    data=llm.complete(prompt)
       
    cleaned_output = data.text.strip() 
    if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[7:] 
    if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]
    return cleaned_output
# 





def main(input):
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None

  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    
    with open("token.json", "w") as token:
      token.write(creds.to_json())
     
  try:
        service = build('calendar', 'v3', credentials=creds)
        cleaned_output=Format(input)
        json_data = json.loads(cleaned_output)
        event = service.events().insert(calendarId='primary', body=json_data).execute()
        print(f'Event created: {event.get("htmlLink")}')
        return cleaned_output
  except HttpError as error:
        print(f"An error occurred: {error}")
        

def Gmail_tool(cleaned_output):
    toolkit = GmailToolkit()
    # Can review scopes here https://developers.google.com/gmail/api/auth/scopes
    # For instance, readonly scope is 'https://www.googleapis.com/auth/gmail.readonly'
    credentials = get_gmail_credentials(
        token_file="token.json",
        scopes=["https://mail.google.com/"],
        client_secrets_file="credentials.json",
    )
    api_resource = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=api_resource)
    tools = toolkit.get_tools()
    llm3 = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    agent = initialize_agent(tools=tools, llm=llm3, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
    agent.invoke(cleaned_output)
    return "Email drafted sucess fully "



calendar_tool = Tool(
        name="Google Calendar Tool",
        func=main,
        description="Add events to Google Calendar based on user input."
    )
    
gmail_tool = Tool(
        name="Gmail Tool",
        func=Gmail_tool,
        description="Drafts an email based on event details as plain text."
    )
    
mainllm=ChatGroq(api_key ="",
             model_name="gemma2-9b-it",temperature=0)    
    # Initialize agent with tools
agent = initialize_agent(
        tools=[calendar_tool, gmail_tool],
        llm=mainllm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
)



agent.invoke("arrange a meeting with jonyy123@gmail.com in monday dec 2024 at 10 am it will be 1 hr meeting in tagore hall and create a confirmation mail")
