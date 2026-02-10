"""In-memory invoice storage (for development/testing)"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Invoice models disabled - Bank statements only
# from api.models import Invoice, InvoiceSummary, InvoiceData, InvoiceMetadata

logger = logging.getLogger(__name__)


class InMemoryInvoiceStore:
    """Invoice storage disabled - bank statements only"""
    pass
