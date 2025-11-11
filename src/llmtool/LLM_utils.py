import concurrent.futures
import json
import os
import signal
import sys
import threading
import time
from functools import partial
from pathlib import Path
from typing import List, Tuple

import boto3
import google.generativeai as genai
import tiktoken
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from openai import *

from utility.errors import RALLMAPIError, RAValueError
from utility.logger import Logger
import anthropic


class LLM:
    """
    A wrapper class for interacting with various LLM providers:
    - Google's Gemini Pro
    - OpenAI models (GPT-3.5, GPT-4, etc)
    - DeepSeek models (V3, R1)
    - Anthropic's Claude (3.5 and 3.7)
    """

    def __init__(
        self,
        online_model_name: str,
        temperature: float = 0.0,
        system_role: str = "You are a experienced programmer and good at understanding programs written in mainstream programming languages.",
        max_output_length: int = 4096,
    ) -> None:
        """
        Initialize the LLM wrapper.

        Args:
            online_model_name: Name/identifier of the LLM model to use
            temperature: Sampling temperature for generation (0.0 = deterministic)
            system_role: System prompt to guide model behavior
            max_output_length: Maximum number of tokens in model response
        """
        self.online_model_name = online_model_name
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-0125")
        self.temperature = temperature
        self.systemRole = system_role
        self.max_output_length = max_output_length

    def infer(
        self, message: str, is_measure_cost: bool = False, log_strs: List[str] = []
    ) -> Tuple[str, int, int, List[str]]:
        """
        Generate a response from the LLM for the given input message.

        Args:
            message: Input text to send to the model
            is_measure_cost: Whether to calculate token usage
            log_strs: List to collect logging messages

        Returns:
            Tuple containing:
            - Generated text response
            - Input token count (if measuring cost)
            - Output token count (if measuring cost)
            - Updated log messages
        """
        log_strs.append(f"{self.online_model_name} is running")
        print("Message: ", message)
        print(self.online_model_name)

        output = ""

        if "gemini" in self.online_model_name:
            output, log_strs = self.infer_with_gemini(message, log_strs)
        elif "gpt" in self.online_model_name:
            output, log_strs = self.infer_with_openai_model(message, log_strs)
        elif "o3-mini" in self.online_model_name or "o4-mini" in self.online_model_name:
            output, log_strs = self.infer_with_On_mini_model(message, log_strs)
        elif "claude" in self.online_model_name:
            output, log_strs = self.infer_with_claude_key(message, log_strs)
        elif "deepseek" in self.online_model_name:
            output, log_strs = self.infer_with_deepseek_model(message, log_strs)
        else:
            raise RAValueError("Unsupported model name")

        input_token_cost = (
            0
            if not is_measure_cost
            else len(self.encoding.encode(self.systemRole))
            + len(self.encoding.encode(message))
        )
        output_token_cost = (
            0 if not is_measure_cost else len(self.encoding.encode(output))
        )

        print("Output: ", output)

        return output, input_token_cost, output_token_cost, log_strs

    def run_with_timeout(
        self, func, timeout: int, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Execute a function with a timeout using ThreadPoolExecutor.

        Args:
            func: Function to execute
            timeout: Maximum execution time in seconds
            log_strs: List to collect logging messages

        Returns:
            Tuple of (function result, updated log messages)
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            try:
                return future.result(timeout=timeout), log_strs
            except concurrent.futures.TimeoutError:
                log_strs.append("Operation timed out")
                return "", log_strs
            except Exception as e:
                log_strs.append(f"Operation failed: {e}")
                return "", log_strs

    def infer_with_gemini(
        self, message: str, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Generate response using Google's Gemini Pro model.

        Args:
            message: Input text for the model
            log_strs: List to collect logging messages

        Returns:
            Tuple of (generated text, updated log messages)
        """
        gemini_model = genai.GenerativeModel("gemini-pro")

        def call_api():
            message_with_role = f"{self.systemRole}\n{message}"
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_DANGEROUS",
                    "threshold": "BLOCK_NONE",
                }
            ]
            response = gemini_model.generate_content(
                message_with_role,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature
                ),
            )
            return response.text

        for attempt in range(5):
            try:
                output, log_strs = self.run_with_timeout(
                    call_api, timeout=50, log_strs=log_strs
                )
                if output:
                    log_strs.append("Inference succeeded...")
                    return output, log_strs
            except Exception as e:
                log_strs.append(f"API error: {e}")
            time.sleep(2)

        return "", log_strs

    def infer_with_openai_model(
        self, message: str, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Generate response using OpenAI models (GPT-3.5, GPT-4, GPT-4o, GPT-5, etc).

        Args:
            message: Input text for the model
            log_strs: List to collect logging messages

        Returns:
            Tuple of (generated text, updated log messages)
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RALLMAPIError(
                "Please set the OPENAI_API_KEY environment variable to use OpenAI models."
            )
        api_key = api_key.split(":")[0]

        model_input = [
            {"role": "system", "content": self.systemRole},
            {"role": "user", "content": message},
        ]

        def call_api():
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.online_model_name,
                messages=model_input,
                temperature=self.temperature,
            )
            return response.choices[0].message.content

        for attempt in range(5):
            try:
                output, log_strs = self.run_with_timeout(
                    call_api, timeout=100, log_strs=log_strs
                )
                if output:
                    log_strs.append("Inference succeeded...")
                    return output, log_strs
            except Exception as e:
                log_strs.append(f"API error: {e}")
            time.sleep(2)

        return "", log_strs

    def infer_with_On_mini_model(
        self, message: str, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Generate response using OpenAI's optimized mini models.

        Args:
            message: Input text for the model
            log_strs: List to collect logging messages

        Returns:
            Tuple of (generated text, updated log messages)
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RALLMAPIError(
                "Please set the OPENAI_API_KEY environment variable to use OpenAI models."
            )
        api_key = api_key.split(":")[0]

        model_input = [
            {"role": "system", "content": self.systemRole},
            {"role": "user", "content": message},
        ]

        def call_api():
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.online_model_name, messages=model_input
            )
            return response.choices[0].message.content

        for attempt in range(5):
            try:
                output, log_strs = self.run_with_timeout(
                    call_api, timeout=100, log_strs=log_strs
                )
                if output:
                    log_strs.append("Inference succeeded...")
                    return output, log_strs
            except Exception as e:
                log_strs.append(f"API error: {e}")
            time.sleep(2)

        return "", log_strs

    def infer_with_deepseek_model(
        self, message: str, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Generate response using DeepSeek models.

        Args:
            message: Input text for the model
            log_strs: List to collect logging messages

        Returns:
            Tuple of (generated text, updated log messages)
        """
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RALLMAPIError(
                "Please set the DEEPSEEK_API_KEY environment variable to use DeepSeek models."
            )

        model_input = [
            {"role": "system", "content": self.systemRole},
            {"role": "user", "content": message},
        ]

        def call_api():
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model=self.online_model_name,
                messages=model_input,
                temperature=self.temperature,
            )
            return response.choices[0].message.content

        for attempt in range(5):
            try:
                output, log_strs = self.run_with_timeout(
                    call_api, timeout=300, log_strs=log_strs
                )
                if output:
                    log_strs.append("Inference succeeded...")
                    return output, log_strs
            except Exception as e:
                log_strs.append(f"API error: {e}")
            time.sleep(2)

        return "", log_strs

    def infer_with_claude_using_bedrock(
        self, message: str, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Generate response using Claude models via AWS Bedrock.

        Args:
            message: Input text for the model
            log_strs: List to collect logging messages

        Returns:
            Tuple of (generated text, updated log messages)
        """
        if "3.5" in self.online_model_name:
            model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        elif "3.7" in self.online_model_name:
            model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        elif "4" in self.online_model_name:
            model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
        else:
            raise RAValueError("Unsupported Claude model name")

        model_input = [
            {"role": "assistant", "content": self.systemRole},
            {"role": "user", "content": message},
        ]

        def call_api():
            client = boto3.client(
                "bedrock-runtime",
                region_name="us-west-2",
                config=Config(read_timeout=300),
            )

            if "thinking" in self.online_model_name:
                if "3.5" in self.online_model_name:
                    raise RAValueError(
                        "Thinking mode is not supported for Claude 3.5 models."
                    )
                body = json.dumps(
                    {
                        "messages": model_input,
                        "max_tokens": self.max_output_length,
                        "thinking": {"type": "enabled", "budget_tokens": 2000},
                        "anthropic_version": "bedrock-2023-05-31",
                    }
                )
            else:
                body = json.dumps(
                    {
                        "messages": model_input,
                        "max_tokens": self.max_output_length,
                        "anthropic_version": "bedrock-2023-05-31",
                        "temperature": self.temperature,
                    }
                )

            response = client.invoke_model(
                modelId=model_id, contentType="application/json", body=body
            )
            response_data = json.loads(response["body"].read().decode("utf-8"))
            return response_data["content"][0]["text"]

        for attempt in range(5):
            try:
                output, log_strs = self.run_with_timeout(
                    call_api, timeout=300, log_strs=log_strs
                )
                if output:
                    log_strs.append("Inference succeeded...")
                    return output, log_strs
            except Exception as e:
                log_strs.append(f"API error: {str(e)}")
            time.sleep(2)

        return "", log_strs

    def infer_with_claude_key(
        self, message: str, log_strs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        Generate response using Claude models via direct API access.

        Args:
            message: Input text for the model
            log_strs: List to collect logging messages

        Returns:
            Tuple of (generated text, updated log messages)
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "Please set the ANTHROPIC_API_KEY environment variable to use Claude models."
            )

        model_input = [{"role": "user", "content": f"{self.systemRole}\n\n{message}"}]

        if "3.5" in self.online_model_name:
            model_id = "claude-3-5-sonnet-20241022"
        elif "3.7" in self.online_model_name:
            model_id = "claude-3-7-sonnet-20250219"
        elif "4" in self.online_model_name:
            model_id = "claude-sonnet-4-20250514"
        else:
            raise RAValueError("Unsupported Claude model name")

        def call_api():
            client = anthropic.Anthropic(api_key=api_key)

            if "thinking" in self.online_model_name:
                if "3.5" in self.online_model_name:
                    raise RAValueError(
                        "Thinking mode is not supported for Claude 3.5 models."
                    )
                api_params = {
                    "model": model_id,
                    "messages": model_input,
                    "max_tokens": self.max_output_length,
                    "temperature": self.temperature,
                    "thinking": {"type": "enabled", "budget_tokens": 2048},
                }

            else:
                api_params = {
                    "model": model_id,
                    "messages": model_input,
                    "max_tokens": self.max_output_length,
                    "temperature": self.temperature,
                }

            response = client.messages.create(**api_params)

            if (
                "3.7" in self.online_model_name
                and hasattr(response, "content")
                and len(response.content) > 1
            ):
                return response.content[-1].text
            return response.content[0].text

        for attempt in range(5):
            try:
                output, log_strs = self.run_with_timeout(
                    call_api, timeout=300, log_strs=log_strs
                )
                if output:
                    log_strs.append(
                        f"Claude API call successful with {self.online_model_name}"
                    )
                    return output, log_strs
            except Exception as e:
                log_strs.append(f"Claude API error (attempt {attempt + 1}/5): {e}")
            time.sleep(2)

        log_strs.append("Max retries reached for Claude API")
        return "", log_strs
