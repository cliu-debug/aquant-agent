"""智能体基类"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from astock_agents.models import StockData


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(
        self,
        name: str,
        role: str,
        llm: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            role: 角色描述
            llm: 语言模型实例（可选）
            config: 配置字典
        """
        self.name = name
        self.role = role
        self.config = config or {}
        self.llm = llm  # LLM是可选的，某些智能体不需要LLM
        
        logger.info(f"智能体初始化: {name} ({role})")
    
    def _create_default_llm(self) -> Optional[Any]:
        """创建默认LLM（如果配置了API密钥）"""
        llm_config = self.config.get("llm", {})
        provider = llm_config.get("default_provider", "openai")
        
        try:
            if provider == "openai":
                api_key = llm_config.get("openai", {}).get("api_key")
                if not api_key:
                    logger.warning(f"[{self.name}] 未配置OpenAI API密钥，LLM功能不可用")
                    return None
                    
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=llm_config.get("openai", {}).get("model", "gpt-4"),
                    temperature=llm_config.get("openai", {}).get("temperature", 0.3),
                    api_key=api_key,
                )
            elif provider == "anthropic":
                api_key = llm_config.get("anthropic", {}).get("api_key")
                if not api_key:
                    logger.warning(f"[{self.name}] 未配置Anthropic API密钥，LLM功能不可用")
                    return None
                    
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(
                    model=llm_config.get("anthropic", {}).get("model", "claude-3-sonnet-20240229"),
                    temperature=llm_config.get("anthropic", {}).get("temperature", 0.3),
                    api_key=api_key,
                )
        except Exception as e:
            logger.warning(f"[{self.name}] LLM初始化失败: {e}")
            return None
        
        return None
    
    @abstractmethod
    def analyze(self, stock_data: StockData, **kwargs) -> Dict[str, Any]:
        """
        执行分析
        
        Args:
            stock_data: 股票数据
            **kwargs: 额外参数
        
        Returns:
            分析结果字典
        """
        pass
    
    def _create_prompt(self, stock_data: StockData, context: Optional[str] = None) -> str:
        """
        创建提示词
        
        Args:
            stock_data: 股票数据
            context: 上下文信息
        
        Returns:
            提示词字符串
        """
        base_prompt = f"""你是{self.name}，角色是{self.role}。

当前分析的股票: {stock_data.stock_name} ({stock_data.stock_code})
当前价格: {stock_data.current_price}
所属行业: {stock_data.industry or '未知'}

"""
        if context:
            base_prompt += f"\n上下文信息:\n{context}\n"
        
        return base_prompt
    
    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        调用LLM
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
        
        Returns:
            LLM回复
        """
        if not self.llm:
            logger.warning(f"[{self.name}] LLM未配置，返回默认响应")
            return "LLM未配置，无法执行分析"
        
        try:
            messages = []
            
            if system_prompt:
                messages.append(("system", system_prompt))
            
            messages.append(("human", prompt))
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"[{self.name}] LLM调用失败: {e}")
            return f"分析失败: {str(e)}"
    
    def log_analysis(self, result: Dict[str, Any]):
        """记录分析结果"""
        logger.info(f"[{self.name}] 分析完成")
        logger.debug(f"[{self.name}] 结果: {result}")
