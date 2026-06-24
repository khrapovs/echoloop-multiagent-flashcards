from google.adk.apps import App

from echoloop.agents.root_agent import root_agent
from echoloop.config import configure_genai

configure_genai()


app = App(root_agent=root_agent, name="echoloop")
