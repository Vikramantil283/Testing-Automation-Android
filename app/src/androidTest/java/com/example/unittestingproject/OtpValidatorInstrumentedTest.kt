package com.example.unittestingproject

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumented tests for OtpValidator — runs directly on the Android device.
 */
@RunWith(AndroidJUnit4::class)
class OtpValidatorInstrumentedTest {

    private lateinit var validator: OtpValidator

    @Before
    fun setUp() {
        validator = OtpValidator()
    }

    // ─── validate() ───────────────────────────────────────────────────────────

    @Test
    fun validate_emptyOtp_returnsError() {
        assertEquals("OTP cannot be empty", validator.validate(""))
    }

    @Test
    fun validate_blankOtp_returnsError() {
        assertEquals("OTP cannot be empty", validator.validate("   "))
    }

    @Test
    fun validate_otpFewerThan6Digits_returnsError() {
        assertEquals("OTP must be 6 digits", validator.validate("12345"))
    }

    @Test
    fun validate_otpMoreThan6Digits_returnsError() {
        assertEquals("OTP must be 6 digits", validator.validate("1234567"))
    }

    @Test
    fun validate_otpWithLetters_returnsError() {
        assertEquals("OTP must contain only digits", validator.validate("12ab56"))
    }

    @Test
    fun validate_otpWithSpecialChars_returnsError() {
        assertEquals("OTP must contain only digits", validator.validate("12@#56"))
    }

    @Test
    fun validate_valid6DigitOtp_returnsNull() {
        assertNull(validator.validate("123456"))
    }

    @Test
    fun validate_allZerosOtp_isStructurallyValid() {
        assertNull(validator.validate("000000"))
    }

    // ─── verify() ─────────────────────────────────────────────────────────────

    @Test
    fun verify_correctOtp_returnsSuccess() {
        assertTrue(validator.verify("123456") is OtpResult.Success)
    }

    @Test
    fun verify_wrongOtp_returnsError() {
        val result = validator.verify("999999")
        assertTrue(result is OtpResult.Error)
        assertEquals("Invalid OTP. Please try again.", (result as OtpResult.Error).message)
    }

    @Test
    fun verify_allZerosOtp_returnsError() {
        val result = validator.verify("000000")
        assertTrue(result is OtpResult.Error)
        assertEquals("Invalid OTP. Please try again.", (result as OtpResult.Error).message)
    }

    @Test
    fun verify_shortOtp_returnsValidationError() {
        val result = validator.verify("123")
        assertTrue(result is OtpResult.Error)
        assertEquals("OTP must be 6 digits", (result as OtpResult.Error).message)
    }

    @Test
    fun verify_emptyOtp_returnsValidationError() {
        val result = validator.verify("")
        assertTrue(result is OtpResult.Error)
        assertEquals("OTP cannot be empty", (result as OtpResult.Error).message)
    }
}
