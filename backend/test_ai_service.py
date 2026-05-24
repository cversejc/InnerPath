"""
测试AI服务是否正常工作
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import generate_report_with_ai


async def test_ai_service():
    """测试AI报告生成"""
    print("=" * 60)
    print("测试 DeepSeek AI 报告生成服务")
    print("=" * 60)

    # 测试数据
    test_user_data = {
        "name": "测试用户",
        "gender": "male",
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 15,
        "birth_hour": 10,
        "birth_minute": 30,
        "selected_topics": ["career", "relationship"],
        "additional_info": "希望了解职业发展方向"
    }

    print("\n测试数据:")
    print(f"  姓名: {test_user_data['name']}")
    print(f"  出生: {test_user_data['birth_year']}-{test_user_data['birth_month']}-{test_user_data['birth_day']}")
    print(f"  关注议题: {test_user_data['selected_topics']}")

    print("\n开始调用 DeepSeek API...")
    print("-" * 60)

    try:
        result = await generate_report_with_ai(test_user_data)

        print("\n✅ AI 调用成功!")
        print("-" * 60)

        # 检查是否使用了AI生成
        if result.get("ai_generated_content"):
            print("\n✅ 使用了 DeepSeek AI 生成报告")
            print(f"\n生成方式: {result['basic_info'].get('generated_by', 'Unknown')}")
            print(f"\nAI 生成内容预览 (前500字符):")
            print("-" * 60)
            content = result["ai_generated_content"]
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print("\n⚠️  使用了降级方案（基础算法）")
            print("可能原因:")
            print("  1. DeepSeek API Key 未配置或无效")
            print("  2. API 调用失败")
            print("  3. 网络连接问题")

        print("\n" + "=" * 60)
        print("报告结构:")
        print(f"  - 基本信息: {bool(result.get('basic_info'))}")
        print(f"  - 能量特质: {bool(result.get('energy_profile'))}")
        print(f"  - 职业建议: {bool(result.get('career_guidance'))}")
        print(f"  - 关系模式: {bool(result.get('relationship_pattern'))}")
        print(f"  - 个人成长: {bool(result.get('personal_growth'))}")
        print(f"  - 总结: {bool(result.get('summary'))}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ai_service())
