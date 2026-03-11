package com.example.unittestingproject

import org.junit.Test
import org.junit.Assert.*

class ForgotPasswordManagerTest {

    private val forgotPasswordManager = ForgotPasswordManager()

    @Test
    fun `validateEmail - should return null for valid email`() {
        val email = "test@example.com"
        val result = forgotPasswordManager.validateEmail(email)
        assertNull(result)
    }

    @Test
    fun `validateEmail - should return error for blank email`() {
        val email = ""
        val result = forgotPasswordManager.validateEmail(email)
        assertEquals("Please enter your email address", result)
    }

    @Test
    fun `validateEmail - should return error for invalid email`() {
        val email = "test@example"
        val result = forgotPasswordManager.validateEmail(email)
        assertEquals("Please enter a valid email address", result)
    }

    @Test
    fun `sendPasswordReset - should return success for valid email`() {
        val email = "test@example.com"
        val result = forgotPasswordManager.sendPasswordReset(email)
        assertTrue(result is ForgotPasswordResult.Success)
        assertEquals(email, (result as ForgotPasswordResult.Success).email)
    }

    @Test
    fun `sendPasswordReset - should return error for blank email`() {
        val email = ""
        val result = forgotPasswordManager.sendPasswordReset(email)
        assertTrue(result is ForgotPasswordResult.Error)
        assertEquals("Please enter your email address", (result as ForgotPasswordResult.Error).message)
    }

    @Test
    fun `sendPasswordReset - should return error for invalid email`() {
        val email = "test@example"
        val result = forgotPasswordManager.sendPasswordReset(email)
        assertTrue(result is ForgotPasswordResult.Error)
        assertEquals("Please enter a valid email address", (result as ForgotPasswordResult.Error).message)
    }
}