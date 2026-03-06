package com.example.unittestingproject

import org.junit.After
import org.junit.Test
import org.junit.Assert.*
import org.junit.Before

class OtpValidatorGeneratedTest {

    private lateinit var validator: OtpValidator

    @Before
    fun setUp() {
        validator = OtpValidator()
    }

    @After
    fun tearDown() {
        validator = OtpValidator()
    }

    // ─── validate() tests ──────────────────────────────────────────────────────

    @Test
    fun `validate - empty OTP returns error`() {
        val result = validator.validate("")
        assertNotNull(result)
        assertEquals("OTP cannot be empty", result)
    }

    @Test
    fun `validate - blank OTP returns error`() {
        val result = validator.validate("   ")
        assertNotNull(result)
        assertEquals("OTP cannot be empty", result)
    }

    @Test
    fun `validate - OTP with fewer than 6 digits returns error`() {
        val result = validator.validate("12345")
        assertNotNull(result)
        assertEquals("OTP must be 6 digits", result)
    }

    @Test
    fun `validate - OTP with more than 6 digits returns error`() {
        val result = validator.validate("1234567")
        assertNotNull(result)
        assertEquals("OTP must be 6 digits", result)
    }

    @Test
    fun `validate - OTP with letters returns error`() {
        val result = validator.validate("12ab56")
        assertNotNull(result)
        assertEquals("OTP must contain only digits", result)
    }

    @Test
    fun `validate - OTP with special characters returns error`() {
        val result = validator.validate("12@#56")
        assertNotNull(result)
        assertEquals("OTP must contain only digits", result)
    }

    @Test
    fun `validate - valid 6-digit OTP returns null`() {
        val result = validator.validate("123456")
        assertNull(result)
    }

    @Test
    fun `validate - all zeros OTP is structurally valid`() {
        val result = validator.validate("000000")
        assertNull(result)
    }

    // ─── verify() tests ────────────────────────────────────────────────────────

    @Test
    fun `verify - correct OTP returns Success`() {
        val result = validator.verify("123456")
        assertTrue(result is OtpResult.Success)
    }

    @Test
    fun `verify - wrong OTP returns Error`() {
        val result = validator.verify("999999")
        assertTrue(result is OtpResult.Error)
        assertEquals("Invalid OTP. Please try again.", (result as OtpResult.Error).message)
    }

    @Test
    fun `verify - all zeros OTP returns Error`() {
        val result = validator.verify("000000")
        assertTrue(result is OtpResult.Error)
        assertEquals("Invalid OTP. Please try again.", (result as OtpResult.Error).message)
    }

    @Test
    fun `verify - short OTP returns validation Error`() {
        val result = validator.verify("123")
        assertTrue(result is OtpResult.Error)
        assertEquals("OTP must be 6 digits", (result as OtpResult.Error).message)
    }

    @Test
    fun `verify - empty OTP returns validation Error`() {
        val result = validator.verify("")
        assertTrue(result is OtpResult.Error)
        assertEquals("OTP cannot be empty", (result as OtpResult.Error).message)
    }
}