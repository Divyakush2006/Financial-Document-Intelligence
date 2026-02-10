"""
Token Optimizer - Dynamically fit maximum data within LLM token limits
Uses fast token counting to maximize context usage
"""

import tiktoken
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Groq model token limits
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 32768  # Total context window
GROQ_OUTPUT_TOKENS = 8000  # Reserved for response
GROQ_PROMPT_OVERHEAD = 500  # System prompt + formatting

# Available for user input
SAFE_INPUT_TOKENS = GROQ_MAX_TOKENS - GROQ_OUTPUT_TOKENS - GROQ_PROMPT_OVERHEAD


class TokenOptimizer:
    """Fast token counting and intelligent truncation"""
    
    def __init__(self):
        # Use tiktoken for fast, accurate token counting
        # cl100k_base is compatible with most LLMs
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback to simple estimation if tiktoken fails
            self.encoder = None
            logger.warning("tiktoken not available, using character estimation")
    
    def count_tokens(self, text: str) -> int:
        """
        Fast token counting
        
        Args:
            text: Input text
            
        Returns:
            Token count
        """
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Fallback: ~4 chars per token (rough estimate)
            return len(text) // 4
    
    def optimize_for_llm(self, text: str, max_tokens: int = SAFE_INPUT_TOKENS) -> Tuple[str, dict]:
        """
        Intelligently truncate text to fit within token limit
        Prioritizes: Header (metadata) → Recent transactions → Sample middle
        
        Args:
            text: Raw extracted text from Excel
            max_tokens: Maximum tokens allowed
            
        Returns:
            Tuple of (optimized_text, stats_dict)
        """
        # Quick check: if already fits, return as-is
        original_tokens = self.count_tokens(text)
        
        if original_tokens <= max_tokens:
            logger.info(f"✅ Text fits: {original_tokens} tokens (limit: {max_tokens})")
            return text, {
                "original_tokens": original_tokens,
                "final_tokens": original_tokens,
                "truncated": False,
                "reduction_pct": 0
            }
        
        logger.info(f"⚠️ Text too large: {original_tokens} tokens (limit: {max_tokens})")
        logger.info(f"🔧 Optimizing to fit maximum data...")
        
        # Split into lines for intelligent sampling
        lines = text.split('\n')
        total_lines = len(lines)
        
        # Priority allocation (percentage of available tokens)
        header_allocation = 0.20  # 20% for header/metadata
        footer_allocation = 0.50  # 50% for recent transactions
        middle_allocation = 0.30   # 30% for middle samples
        
        # Calculate token budgets
        header_budget = int(max_tokens * header_allocation)
        footer_budget = int(max_tokens * footer_allocation)
        middle_budget = int(max_tokens * middle_allocation)
        
        # Extract sections
        header_lines = []
        footer_lines = []
        middle_lines = []
        
        # 1. Build header (first N lines until budget exhausted)
        header_tokens = 0
        for i, line in enumerate(lines[:100]):  # Max 100 lines for header
            line_tokens = self.count_tokens(line)
            if header_tokens + line_tokens > header_budget:
                break
            header_lines.append(line)
            header_tokens += line_tokens
        
        header_end_idx = len(header_lines)
        
        # 2. Build footer (last N lines until budget exhausted)
        footer_tokens = 0
        for line in reversed(lines[-200:]):  # Max 200 lines for footer
            line_tokens = self.count_tokens(line)
            if footer_tokens + line_tokens > footer_budget:
                break
            footer_lines.insert(0, line)
            footer_tokens += line_tokens
        
        footer_start_idx = total_lines - len(footer_lines)
        
        # 3. Sample middle (every Nth line to fit budget)
        middle_section = lines[header_end_idx:footer_start_idx]
        if middle_section:
            # Calculate sampling rate
            middle_tokens = 0
            sample_rate = max(1, len(middle_section) // 50)  # Sample ~50 lines
            
            for i in range(0, len(middle_section), sample_rate):
                line = middle_section[i]
                line_tokens = self.count_tokens(line)
                if middle_tokens + line_tokens > middle_budget:
                    break
                middle_lines.append(line)
                middle_tokens += line_tokens
        
        # Combine sections
        optimized_text = '\n'.join([
            *header_lines,
            "",
            f"[... {len(middle_section) - len(middle_lines)} middle transactions omitted, showing sample ...]",
            "",
            *middle_lines,
            "",
            f"[... Recent {len(footer_lines)} transactions ...]",
            "",
            *footer_lines
        ])
        
        final_tokens = self.count_tokens(optimized_text)
        reduction_pct = ((original_tokens - final_tokens) / original_tokens) * 100
        
        stats = {
            "original_tokens": original_tokens,
            "final_tokens": final_tokens,
            "truncated": True,
            "reduction_pct": round(reduction_pct, 1),
            "original_lines": total_lines,
            "header_lines": len(header_lines),
            "middle_samples": len(middle_lines),
            "footer_lines": len(footer_lines),
            "header_tokens": header_tokens,
            "middle_tokens": middle_tokens if middle_lines else 0,
            "footer_tokens": footer_tokens
        }
        
        logger.info(f"✅ Optimized: {original_tokens} → {final_tokens} tokens ({reduction_pct:.1f}% reduction)")
        logger.info(f"📊 Sections: Header={len(header_lines)} | Middle={len(middle_lines)} | Footer={len(footer_lines)}")
        
        return optimized_text, stats


# Singleton instance
_optimizer_instance = None

def get_token_optimizer() -> TokenOptimizer:
    """Get or create token optimizer singleton"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = TokenOptimizer()
    return _optimizer_instance
