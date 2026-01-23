import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock langchain modules before importing app.rag
sys.modules['langchain_chroma'] = MagicMock()
sys.modules['langchain_ollama'] = MagicMock()
sys.modules['langchain_community.document_loaders'] = MagicMock()
sys.modules['langchain_text_splitters'] = MagicMock()

from app.rag import infer_category_from_filename, get_retriever

class TestRAGChanges(unittest.TestCase):
    def test_infer_category(self):
        cases = {
            "claims_process.pdf": "claims",
            "payment_gateway.pdf": "payment",
            "security_policy_v2.pdf": "policy",
            "faq_2024.pdf": "faq",
            "SOP_handling.pdf": "sop",
            "random_document.pdf": "general",
            "Claims_Report.pdf": "claims" # Case insensitive
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(infer_category_from_filename(filename), expected)

    @patch('app.rag.get_vector_store')
    def test_get_retriever_filter(self, mock_get_store):
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        
        # Test without category
        get_retriever()
        mock_store.as_retriever.assert_called_with(search_kwargs={"k": 3})
        
        # Test with category
        get_retriever(category="claims")
        mock_store.as_retriever.assert_called_with(search_kwargs={"k": 3, "filter": {"category": "claims"}})

if __name__ == '__main__':
    unittest.main()
