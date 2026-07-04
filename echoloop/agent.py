from google.adk.apps import App

from echoloop.agents.context_agent import context_agent
from echoloop.config import configure_genai

configure_genai()


app = App(root_agent=context_agent, name="echoloop")
