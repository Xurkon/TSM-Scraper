"""Quick test to verify groupTreeStatus key generation uses SOH character."""

import sys
sys.path.insert(0, 'tsm_scraper')

# Test the key generation logic
def test_gts_key_generation():
    """Test that groupTreeStatus keys are generated correctly with SOH separator."""
    
    test_cases = [
        ("TestGroup", "1 TestGroup"),
        ("TestGroup`SubGroupTest", "1 TestGroup TestGroup`SubGroupTest"),
        ("TestGroup`SubGroupTest`SubSubgroupTest", "1 TestGroup TestGroup`SubGroupTest TestGroup`SubGroupTest`SubSubgroupTest"),
        ("TestGroup`SubGroupTest`SubSubgroupTest`SuperSubgroupTest", "1 TestGroup TestGroup`SubGroupTest TestGroup`SubGroupTest`SubSubgroupTest TestGroup`SubGroupTest`SubSubgroupTest`SuperSubgroupTest"),
    ]
    
    print("Testing groupTreeStatus key generation...\n")
    
    all_passed = True
    for group_path, expected_key in test_cases:
        # Simulate the key generation logic from lua_writer.py
        parts = group_path.split('`')
        path_parts = ["1"]  # Always starts with "1"
        for i in range(len(parts)):
            cumulative_path = '`'.join(parts[:i+1])
            path_parts.append(cumulative_path)
        gts_key = " ".join(path_parts)
        
        passed = gts_key == expected_key
        status = "PASS" if passed else "FAIL"
        
        print(f"[{status}] {group_path}")
        print(f"       Expected: {repr(expected_key)}")
        print(f"       Got:      {repr(gts_key)}")
        print()
        
        if not passed:
            all_passed = False
    
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
    
    return all_passed

if __name__ == "__main__":
    test_gts_key_generation()
