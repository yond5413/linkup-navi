import asyncio
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.linkup import LinkupClient


async def test_linkup_async():
    """Test async_search method specifically."""
    print("Testing LinkupClient async_search method...")
    client = LinkupClient()

    if not client.client:
        print("[WARN] No API key configured - testing mock mode")
        result = await client.search("test query")
        print(f"Mock result keys: {list(result.keys())}")
        return

    try:
        result = await client.client.async_search(
            query="Microsoft revenue 2024", depth="deep", output_type="sourcedAnswer"
        )
        print("[OK] async_search succeeded!")
        print(f"   Response type: {type(result)}")
        print(f"   Has answer: {hasattr(result, 'answer')}")
        print(f"   Has sources: {hasattr(result, 'sources')}")
        if hasattr(result, "answer"):
            print(f"   Answer preview: {result.answer[:100]}...")
        if hasattr(result, "sources"):
            print(f"   Sources count: {len(result.sources)}")
    except Exception as e:
        print(f"[ERROR] async_search failed: {e}")
        import traceback

        traceback.print_exc()


async def test_linkup_wrapper():
    """Test the wrapper search method."""
    print("\nTesting LinkupClient.search() wrapper...")
    client = LinkupClient()

    result = await client.search("Microsoft revenue 2024")
    print(f"Result keys: {list(result.keys())}")
    answer = result.get("answer", "None")
    print(
        f"Search Answer: {answer[:100] if answer and answer != 'None' else 'None'}..."
    )
    print(f"Sources count: {len(result.get('sources', []))}")

    if result.get("answer") and result.get("sources"):
        print("[OK] Wrapper returns valid response structure")
        return True
    else:
        print("[ERROR] Wrapper missing expected fields")
        return False


async def test_get_company_info():
    """Test get_company_info method."""
    print("\nTesting get_company_info()...")
    client = LinkupClient()
    result = await client.get_company_info("Microsoft")

    print(f"Result keys: {list(result.keys())}")
    if "answer" in result and "sources" in result:
        print("[OK] get_company_info returns valid structure")
        return True
    return False


async def run_all_tests():
    """Run all Linkup tests."""
    print("=" * 60)
    print("LINKUP CLIENT TEST SUITE")
    print("=" * 60)

    await test_linkup_async()
    await test_linkup_wrapper()
    await test_get_company_info()

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
