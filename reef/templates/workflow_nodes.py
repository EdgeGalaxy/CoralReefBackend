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
                },
            "params": {
                "type": "array",
                "title": "Parameters",
                "cn_title": "参数列表",
                "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "title": "参数名称"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["string", "number", "boolean", "dict"],
                        "title": "参数类型",
                        "default": "number"
                    },
                    "value": {
                        "anyOf": [
                            {
                                "type": "string",
                                "title": "字符串",
                                "x-display-if": {
                                    "field": "type",
                                    "value": "string"
                                }
                  },
                  {
                                "type": "number",
                                "title": "数值",
                                "x-display-if": {
                                    "field": "type",
                                    "value": "number"
                                }
                  },
                  {
                                "type": "boolean",
                                "title": "布尔值",
                                "x-display-if": {
                                    "field": "type",
                                    "value": "boolean"
                                }
                  },
                  {
                                "type": "object",
                                "title": "JSON对象",
                                "x-display-if": {
                                    "field": "type",
                                    "value": "dict"
                                }
                  }
                ]
              }
            },
                "required": ['name', 'type', 'value']
            }
        }},
    },
    "formData": {}
    },
    "width": 147,
    "height": 133
}

STEP_NODE_TEMPLATE = {
    "id": "",  # 将被替换为实际的节点ID
    "type": "customNode",
    "position": {"x": 0, "y": 0},  # 将被替换为实际的位置
    "data": {
        "block_schema": {},
        "formData": {},  # 将被替换为实际的表单数据
    },
    "width": 200,
    "height": 77,
    "style": {
        "width": 200,
        "fontSize": "12px"
    },
    "selected": True,
    "positionAbsolute": {
        "x": 160,
        "y": 140
    },
    "dragging": False
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
                            "name": {
                                "type": "string",
                                "title": "Name",
                                "cn_title": "参数名称"
                            },
                            "value": {
                                "title": "Value",
                                "cn_title": "参数值",
                                "anyOf": [
                                    {
                                        "kind": [
                                        {
                                            "description": "String value",
                                            "docs": "\nExamples:\n```\n\"my string value\"\n```\n",
                                            "name": "string"
                                        }
                    ],
                    "pattern": "^\\$inputs.[A-Za-z_0-9\\-]+$",
                    "reference": True,
                    "selected_element": "workflow_parameter",
                    "type": "string"
                  },
                  {
                    "kind": [
                      {
                        "description": "Image in workflows",
                        "docs": '\nThis is the representation of image in `workflows`. The value behind this kind \nis Python list of dictionaries. Each of this dictionary is native `inference` image with\nthe following keys defined:\n```python\n{\n    "type": "url",   # there are different types supported, including np arrays and PIL images\n    "value": "..."   # value depends on `type`\n}\n```\nThis format makes it possible to use [inference image utils](https://inference.roboflow.com/docs/reference/inference/core/utils/image_utils/)\nto operate on the images. \n\nSome blocks that output images may add additional fields - like "parent_id", which should\nnot be modified but may be used is specific contexts - for instance when\none needs to tag predictions with identifier of parent image.\n',
                        "name": 'image'
                      }
                    ],
                    "pattern": "^\\$inputs.[A-Za-z_0-9\\-]+$",
                    "reference": True,
                    "selected_element": "any_data",
                    "type": "string"
                  },
                  {
                    "kind": [
                      {
                        "description": "Image in workflows",
                        "docs": '\nThis is the representation of image in `workflows`. The value behind this kind \nis Python list of dictionaries. Each of this dictionary is native `inference` image with\nthe following keys defined:\n```python\n{\n    "type": "url",   # there are different types supported, including np arrays and PIL images\n    "value": "..."   # value depends on `type`\n}\n```\nThis format makes it possible to use [inference image utils](https://inference.roboflow.com/docs/reference/inference/core/utils/image_utils/)\nto operate on the images. \n\nSome blocks that output images may add additional fields - like "parent_id", which should\nnot be modified but may be used is specific contexts - for instance when\none needs to tag predictions with identifier of parent image.\n',
                        "name": 'image'
                      }
                    ],
                    "pattern": "^\\$steps\\.[A-Za-z_\\-0-9]+\\.[A-Za-z_*0-9\\-]+$",
                    "reference": True,
                    "selected_element": "step_output",
                    "type": "string"
                  }
                ]
              }
            },
            "required": ['name', 'value']
          }
        }
      }
    },
        "formData": {},
    },
    "width": 171,
    "height": 105
} 