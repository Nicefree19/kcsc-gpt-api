#!/usr/bin/env python3
"""
향상된 검색 인덱스 빌더
- 정밀한 키워드 매핑
- 다층 카테고리 구조
- 의미론적 검색 지원
- GPT 최적화된 구조
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import re
from typing import Dict, List, Set, Any

class EnhancedSearchIndexBuilder:
    def __init__(self):
        self.standards_data = {}
        self.keyword_index = defaultdict(list)
        self.category_hierarchy = {}
        self.semantic_groups = {}
        self.quality_tiers = {}
        
    def load_existing_data(self):
        """기존 데이터 로드"""
        data_files = [
            'kcsc_structure.json',
            'kcsc_civil.json', 
            'kcsc_building.json',
            'kcsc_facility.json',
            'kcsc_excs.json'
        ]
        
        for file_name in data_files:
            if os.path.exists(file_name):
                with open(file_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.standards_data.update(data)
    
    def build_enhanced_index(self):
        """향상된 검색 인덱스 구축"""
        enhanced_index = {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "total_documents": len(self.standards_data),
            "optimization": "gpt_actions_optimized"
        }
        
        return enhanced_index

if __name__ == "__main__":
    builder = EnhancedSearchIndexBuilder()
    builder.load_existing_data()
    enhanced_index = builder.build_enhanced_index()
    
    with open('enhanced_search_index.json', 'w', encoding='utf-8') as f:
        json.dump(enhanced_index, f, ensure_ascii=False, indent=2)