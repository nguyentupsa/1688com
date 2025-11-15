import os
import logging
from typing import Dict, Any, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from settings import settings

logger = logging.getLogger(__name__)

class AIClient:
    """Google AI client for negotiation message generation."""

    def __init__(self):
        self.api_key = settings.google_api_key
        self.model_name = settings.google_model
        self._client = None
        self._init_error = None

        # Validate API key format
        if self.api_key:
            if not self.api_key.startswith('AIza'):
                logger.error(f"[AI] Invalid Google API key format. Expected to start with 'AIza', got: {self.api_key[:10]}...")
                self._init_error = "Invalid API key format"
                self.api_key = None
            elif len(self.api_key) < 20:
                logger.error(f"[AI] Google API key too short. Expected at least 20 characters, got: {len(self.api_key)}")
                self._init_error = "API key too short"
                self.api_key = None

        if self.api_key:
            try:
                logger.info(f"[AI] Initializing Google AI with model: {self.model_name}")
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(
                    model_name=self.model_name,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                # Test the connection with a simple prompt
                test_result = self._client.generate_content("Hello")
                if test_result and test_result.text:
                    logger.info(f"[AI] ✅ Google AI successfully initialized with model: {self.model_name}")
                else:
                    logger.warning("[AI] Google AI initialization test failed - using mock responses")
                    self._client = None
                    self._init_error = "API test failed"
            except Exception as e:
                logger.error(f"[AI] ❌ Failed to initialize Google AI: {type(e).__name__}: {str(e)}")
                self._client = None
                self._init_error = str(e)
                # Provide helpful guidance based on error type
                if "permission" in str(e).lower() or "forbidden" in str(e).lower():
                    logger.error("[AI] API key appears to be invalid or lacks permissions. Please check your Google AI Studio API key.")
                elif "quota" in str(e).lower() or "limit" in str(e).lower():
                    logger.error("[AI] API quota exceeded. Please check your Google AI usage limits.")
                elif "network" in str(e).lower() or "connection" in str(e).lower():
                    logger.error("[AI] Network connection failed. Please check your internet connection.")
                else:
                    logger.error("[AI] Using mock responses due to initialization failure.")
        else:
            logger.warning("[AI] ⚠️  No valid GOOGLE_API_KEY provided - using intelligent mock responses")
            self._init_error = "No API key provided"

    def is_available(self) -> bool:
        return self._client is not None

    def get_status(self) -> Dict[str, Any]:
        """Get detailed AI client status."""
        return {
            "is_available": self.is_available(),
            "api_key_configured": bool(self.api_key),
            "model_name": self.model_name,
            "init_error": self._init_error,
            "using_mock": not self.is_available()
        }

    async def generate_next_reply(
        self,
        history: List[Dict[str, str]],
        supplier_text: str,
        goals: Dict[str, Any],
        product_url: str,
        locale: str = "zh"
    ) -> Dict[str, Any]:
        """
        Generate the next negotiation reply based on conversation history and goals.

        Args:
            history: List of previous messages with 'role' and 'text'
            supplier_text: Latest supplier message
            goals: Negotiation goals dictionary
            product_url: Product page URL
            locale: Language preference ('zh', 'en', etc.)

        Returns:
            Dict with 'text', 'used_model', 'is_mock' keys
        """

        if not self.is_available():
            return self._generate_mock_response(history, supplier_text, goals, locale)

        try:
            # Build context from history
            context_history = "\n".join([f"{msg['role']}: {msg['text']}" for msg in history])

            # Build goals text
            goals_text = []
            if goals.get('target_price'):
                goals_text.append(f"Target price: {goals['target_price']}")
            if goals.get('moq'):
                goals_text.append(f"MOQ: {goals['moq']}")
            if goals.get('lead_time'):
                goals_text.append(f"Lead time: {goals['lead_time']}")
            if goals.get('quality_requirements'):
                goals_text.append(f"Quality: {goals['quality_requirements']}")
            if goals.get('samples'):
                goals_text.append("Request samples")
            if goals.get('shipping_terms'):
                goals_text.append(f"Shipping: {goals['shipping_terms']}")
            if goals.get('payment_terms'):
                goals_text.append(f"Payment: {goals['payment_terms']}")
            if goals.get('style'):
                goals_text.append(f"Style: {goals['style']}")

            goals_str = "\n".join(goals_text) if goals_text else "Standard B2B inquiry"

            # Determine language
            is_chinese_context = (
                locale == "zh" or
                any(c in supplier_text for c in "的你了是在有我他对她这那之个得地") or
                len(history) > 0 and any(c in history[0].get('text', '') for c in "的你了是在有我他对她这那之个得地")
            )

            # Check for aggressive style
            is_aggressive = goals.get('style', '').lower() == 'aggressive'

            # Build prompt
            if is_chinese_context:
                style_instruction = "使用激进的谈判语气，专注于推动更好的价格和更快的交货期。" if is_aggressive else "保持礼貌和专业。"
                prompt = f"""你是一个专业的1688采购谈判助手。请根据对话历史和采购目标生成简洁的回复。

产品链接: {product_url}

采购目标:
{goals_str}

对话历史:
{context_history}

供应商最新消息: "{supplier_text}"

{style_instruction}

请生成1-2句话的回复，专注于未解决的关键信息（价格、MOQ、交期、样品等）。如果供应商用中文回复，请用中文回复。"""
            else:
                style_instruction = "Use an aggressive negotiation tone focused on pushing better prices and faster delivery." if is_aggressive else "Be professional and goal-oriented."
                prompt = f"""You are a professional B2B negotiation assistant for 1688.com. Generate a concise reply based on conversation history and goals.

Product URL: {product_url}

Goals:
{goals_str}

Conversation History:
{context_history}

Latest supplier message: "{supplier_text}"

{style_instruction}

Generate a 1-2 sentence reply focusing on missing key details (price, MOQ, lead time, samples, etc.). Use simple English unless supplier uses Chinese."""

            # Generate response
            result = self._client.generate_content(prompt)
            text = result.text.strip()

            if not text:
                logger.warning("[AI] Empty response from Google AI, using mock")
                return self._generate_mock_response(history, supplier_text, goals, locale)

            logger.info(f"[AI]  Generated reply via {self.model_name}: {text[:100]}...")
            return {
                "text": text,
                "used_model": self.model_name,
                "is_mock": False
            }

        except Exception as e:
            logger.error(f"[AI]  API call failed: {e}, falling back to mock")
            return self._generate_mock_response(history, supplier_text, goals, locale)

    def _generate_mock_response(
        self,
        history: List[Dict[str, str]],
        supplier_text: str,
        goals: Dict[str, Any],
        locale: str = "zh"
    ) -> Dict[str, Any]:
        """Generate an intelligent mock response when AI is unavailable."""

        # Check if supplier mentioned specific details we should follow up on
        supplier_lower = supplier_text.lower()

        # Determine language with better detection
        is_chinese_context = (
            locale == "zh" or
            any(c in supplier_text for c in "的你了是在有我他对她这那之个得地") or
            (len(history) > 0 and any(c in history[0].get('text', '') for c in "的你了是在有我他对她这那之个得地"))
        )

        # Determine conversation stage
        turn_count = len(history)
        is_early_stage = turn_count <= 2
        is_mid_stage = 2 < turn_count <= 4
        is_late_stage = turn_count > 4

        # Extract context from history
        price_mentioned = any('price' in msg.get('text', '').lower() or '价格' in msg.get('text', '') or '元' in msg.get('text', '') for msg in history)
        moq_mentioned = any('moq' in msg.get('text', '').lower() or '起订' in msg.get('text', '') for msg in history)
        lead_time_mentioned = any('lead time' in msg.get('text', '').lower() or '交期' in msg.get('text', '') for msg in history)

        # Priority-based intelligent responses
        mock_response = ""

        # Handle direct questions from supplier
        if any(keyword in supplier_lower for keyword in ['what', '什么', 'how', '如何', 'which', '哪个']):
            if is_chinese_context:
                mock_response = "我们正在评估多个供应商，需要比较价格和服务。请提供详细的报价信息。"
            else:
                mock_response = "We're evaluating multiple suppliers and need to compare pricing and services. Please provide detailed quotation information."

        # Price-related responses
        elif any(keyword in supplier_lower for keyword in ['price', '价格', 'yuan', '元', '$', 'cost', '费用']):
            if is_early_stage:
                if is_chinese_context:
                    mock_response = "谢谢报价。请问最小起订量是多少？交货期多久？支持定制和开增票吗？"
                else:
                    mock_response = "Thank you for the pricing. What is the MOQ and lead time? Do you support customization and VAT invoices?"
            elif is_mid_stage:
                if is_chinese_context:
                    mock_response = "了解了价格。如果订购1000件以上，价格能优惠多少？样品费用如何计算？"
                else:
                    mock_response = "Price noted. Any discount for orders over 1000 pieces? How about sample costs?"
            else:
                if is_chinese_context:
                    mock_response = "价格基本确认。请问付款方式是什么？是否支持分期付款？"
                else:
                    mock_response = "Price is mostly confirmed. What are the payment terms? Do you support installment payments?"

        # MOQ-related responses
        elif any(keyword in supplier_lower for keyword in ['moq', '起订', 'quantity', '数量', 'minimum']):
            if is_chinese_context:
                mock_response = "MOQ了解了。请问这个价格对应多少数量？是否包含运费和税费？"
            else:
                mock_response = "MOQ understood. Does this price include shipping and taxes? What about sample availability?"

        # Lead time/delivery responses
        elif any(keyword in supplier_lower for keyword in ['lead time', '交期', 'delivery', 'delivery time', 'production', '生产']):
            if is_chinese_context:
                mock_response = "交期确认。请问样品制作时间多久？加急订单如何处理？"
            else:
                mock_response = "Lead time confirmed. How long for sample production? Can you handle rush orders?"

        # Quality/certification responses
        elif any(keyword in supplier_lower for keyword in ['quality', '质量', 'certification', '认证', 'standard', '标准']):
            if is_chinese_context:
                mock_response = "质量标准很重要。请问有哪些认证证书？是否支持第三方验货？"
            else:
                mock_response = "Quality standards are important. What certifications do you have? Do you support third-party inspection?"

        # Customization responses
        elif any(keyword in supplier_lower for keyword in ['custom', '定制', 'customize', 'oem', 'odm']):
            if is_chinese_context:
                mock_response = "定制需求可以讨论。请问定制费用和最低起订量是多少？"
            else:
                mock_response = "Customization can be discussed. What are the costs and MOQ for customized orders?"

        # Sample requests
        elif any(keyword in supplier_lower for keyword in ['sample', '样品', 'specimen', '样品费']):
            if is_chinese_context:
                mock_response = "样品需要确认质量。请问样品费用多少？是否可以退还？"
            else:
                mock_response = "We need samples for quality confirmation. What's the sample cost? Is it refundable?"

        # Default intelligent responses based on conversation stage and goals
        else:
            if is_early_stage:
                # Early stage: gather basic information
                if goals.get('target_price'):
                    if is_chinese_context:
                        mock_response = "谢谢回复。我们的目标价格范围是多少？量大能优惠吗？"
                    else:
                        mock_response = "Thanks for your reply. What's your target price range? Any discount for bulk orders?"
                else:
                    if is_chinese_context:
                        mock_response = "谢谢，我想了解更多产品详情。请问最小起订量、单价区间和交货期？"
                    else:
                        mock_response = "Thank you, I'd like more product details. What are the MOQ, price range, and lead time?"

            elif is_mid_stage:
                # Mid stage: negotiate specific terms
                if is_chinese_context:
                    mock_response = "基本了解了。请问付款方式是什么？是否支持30%定金，70%发货前付清？"
                else:
                    mock_response = "Basic information understood. What are the payment terms? Do you support 30% deposit, 70% before shipment?"

            else:
                # Late stage: final confirmation
                if is_chinese_context:
                    mock_response = "条件基本确认，我需要和团队讨论一下。请问报价有效期多久？"
                else:
                    mock_response = "Terms are mostly confirmed. I need to discuss with my team. How long is the quotation valid?"

        # Add AI mode indicator to response for transparency
        mode_indicator = "🤖 [智能模式] " if not self.is_available() else ""

        logger.info(f"[AI] 🤖 Generated intelligent mock response: {mock_response}")
        return {
            "text": mock_response,
            "used_model": "mock-enhanced",
            "is_mock": True,
            "ai_status": self.get_status()
        }

# Global AI client instance
ai_client = AIClient()