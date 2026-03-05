package com.example.unittestingproject

import org.junit.After
import org.junit.Assert.*
import org.junit.Before

class ForgotPasswordManagerGeneratedTest {

    private lateinit var forgotPasswordManager: ForgotPasswordManager

    @Before
    fun setUp() {
        forgotPasswordManager = ForgotPasswordManager()
    }

    @After
    fun tearDown() {
        // No-op for this example
    }

    fun `sendPasswordReset - valid email`() {
        val result = forgotPasswordManager.sendPasswordReset("test@example.com")
        assertTrue(result is ForgotPasswordResult.Success)
        assertEquals("test@example.com", (result as ForgotPasswordResult.Success).email)
    }

    fun `sendPasswordReset - blank email`() {
        val result = forgotPasswordManager.sendPasswordReset("")
        assertTrue(result is ForgotPasswordResult.Error)
        assertEquals("Please enter your email address", (result as ForgotPasswordResult.Error).message)
    }

    fun `sendPasswordReset - null email`() {
        val result = forgotPasswordManager.sendPasswordReset(null)
        assertTrue(result is ForgotPasswordResult.Error)
        assertEquals("Please enter your email address", (result as ForgotPasswordResult.Error).message)
    }

    fun `sendPasswordReset - invalid email`() {
        val result = forgotPasswordManager.sendPasswordReset("invalid-email")
        assertTrue(result is ForgotPasswordResult.Error)
        assertEquals("Please enter a valid email address", (result as ForgotPasswordResult.Error).message)
    }

    fun `validateEmail - valid email`() {
        val result = forgotPasswordManager.validateEmail("test@example.com")
        assertNull(result)
    }

    fun `validateEmail - blank email`() {
        val result = forgotPasswordManager.validateEmail("")
        assertEquals("Please enter your email address", result)
    }

    fun `validateEmail - null email`() {
        val result = forgotPasswordManager.validateEmail(null)
        assertEquals("Please enter your email address", result)
    }

    fun `validateEmail - invalid email`() {
        val result = forgotPasswordManager.validateEmail("invalid-email")
        assertEquals("Please enter a valid email address", result)
    }
}