"""工作流节点模板"""

INPUT_NODE_TEMPLATE = {
    "id": "input-node",
    "type": "builtInNode",
    "position": {"x": -20, "y": 0},
    "data": {
        "human_friendly_block_name": "Input",
        "manifest_type_identifier": "input",
        "block_schema": {
            "block_type": "buildin",
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "title": "Sources",
                    "cn_title": "输入源",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                }
            }
        },
        "formData": {
            "sources": []  # 将被替换为实际的输入源
        },
        "label": "Input Node"
    },
    "width": 147,
    "height": 133
}

STEP_NODE_TEMPLATE = {
    "id": "",  # 将被替换为实际的节点ID
    "type": "customNode",
    "position": {"x": 0, "y": 0},  # 将被替换为实际的位置
    "data": {
        "block_schema": {
            "block_type": "model",
            "properties": {}  # 将被替换为实际的步骤属性
        },
        "formData": {},  # 将被替换为实际的表单数据
        "label": ""  # 将被替换为实际的标签
    },
    "width": 200,
    "height": 77
}

OUTPUT_NODE_TEMPLATE = {
    "id": "output-node",
    "type": "builtInNode",
    "position": {"x": 460, "y": 40},
    "data": {
        "human_friendly_block_name": "Output",
        "manifest_type_identifier": "output",
        "block_schema": {
            "block_type": "buildin",
            "type": "object",
            "properties": {
                "params": {
                    "type": "array",
                    "title": "Parameters",
                    "cn_title": "参数列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "string"}
                        }
                    }
                }
            }
        },
        "formData": {
            "params": []  # 将被替换为实际的输出参数
        },
        "label": "Output Node"
    },
    "width": 171,
    "height": 105
} 