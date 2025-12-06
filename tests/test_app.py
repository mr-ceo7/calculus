#!/usr/bin/env python3
"""
Test script for Smart Notes Generator Flask App
Tests the upload and conversion functionality programmatically
"""

import requests
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"

def test_homepage():
    """Test that the homepage loads correctly"""
    print("Testing homepage...")
    try:
        response = requests.get(BASE_URL)
        assert response.status_code == 200
        assert "Smart Notes Generator" in response.text
        print("✅ Homepage loads successfully")
        return True
    except Exception as e:
        print(f"❌ Homepage test failed: {e}")
        return False

def test_file_upload(test_file_path):
    """Test file upload and conversion"""
    print(f"\nTesting file upload with: {test_file_path}")
    try:
        if not os.path.exists(test_file_path):
            print(f"❌ Test file not found: {test_file_path}")
            return False
        
        with open(test_file_path, 'rb') as f:
            files = {'file': (os.path.basename(test_file_path), f)}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        
        # Check if we got a file download response
        if response.status_code == 200:
            # Verify it's an HTML file
            if 'text/html' in response.headers.get('Content-Type', ''):
                print("✅ File converted successfully")
                print(f"   Response size: {len(response.content)} bytes")
                
                # Save test output
                output_path = "test_output.html"
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"   Output saved to: {output_path}")
                return True
            else:
                print(f"❌ Unexpected content type: {response.headers.get('Content-Type')}")
                return False
        else:
            print(f"❌ Upload failed with status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

def test_invalid_file():
    """Test that invalid files are rejected"""
    print("\nTesting invalid file rejection...")
    try:
        # Create a temporary invalid file
        invalid_content = b"This is not a valid PDF or TXT file"
        files = {'file': ('test.invalid', invalid_content)}
        response = requests.post(f"{BASE_URL}/upload", files=files, allow_redirects=False)
        
        # Should redirect with error message
        if response.status_code in [302, 303]:
            print("✅ Invalid file correctly rejected")
            return True
        else:
            print(f"❌ Expected redirect, got: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Invalid file test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Smart Notes Generator - Test Suite")
    print("=" * 60)
    
    # Check if Flask server is running
    try:
        requests.get(BASE_URL, timeout=2)
    except requests.exceptions.ConnectionError:
        print("\n❌ Flask server is not running!")
        print("Please start the server with: python app.py")
        return
    
    results = []
    
    # Run tests
    results.append(("Homepage", test_homepage()))
    
    # Test with the sma103_text.txt file (now in data folder)
    test_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'sma103_text.txt')
    if os.path.exists(test_file):
        results.append(("File Upload (TXT)", test_file_upload(test_file)))
    else:
        print(f"\n⚠️  Skipping upload test - {test_file} not found")
    
    results.append(("Invalid File Rejection", test_invalid_file()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
