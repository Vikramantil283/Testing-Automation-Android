package com.example.unittestingproject

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class LoginValidatorTest {

    private lateinit var validator: LoginValidator

    @Before
    fun setUp() {
        validator = LoginValidator()
    }

    // ─── Email Validation Tests ────────────────────────────────────────────────

    @Test
    fun `validateEmail - empty email returns error`() {
        val result = validator.validateEmail("")
        assertNotNull(result)
        assertEquals("Email cannot be empty", result)
    }

    @Test
    fun `validateEmail - blank email returns error`() {
        val result = validator.validateEmail("   ")
        assertNotNull(result)
        assertEquals("Email cannot be empty", result)
    }

    @Test
    fun `validateEmail - missing at-sign returns error`() {
        val result = validator.validateEmail("invalidemail.com")
        assertNotNull(result)
        assertEquals("Enter a valid email address", result)
    }

    @Test
    fun `validateEmail - missing domain returns error`() {
        val result = validator.validateEmail("user@")
        assertNotNull(result)
        assertEquals("Enter a valid email address", result)
    }

    @Test
    fun `validateEmail - valid email returns null`() {
        val result = validator.validateEmail("user@example.com")
        assertNull(result)
    }

    // ─── Password Validation Tests ─────────────────────────────────────────────

    @Test
    fun `validatePassword - empty password returns error`() {
        val result = validator.validatePassword("")
        assertNotNull(result)
        assertEquals("Password cannot be empty", result)
    }

    @Test
    fun `validatePassword - blank password returns error`() {
        val result = validator.validatePassword("   ")
        assertNotNull(result)
        assertEquals("Password cannot be empty", result)
    }

    @Test
    fun `validatePassword - too short password returns error`() {
        val result = validator.validatePassword("abc")
        assertNotNull(result)
        assertEquals("Password must be at least 6 characters", result)
    }

    @Test
    fun `validatePassword - exactly 5 chars returns error`() {
        val result = validator.validatePassword("12345")
        assertNotNull(result)
        assertEquals("Password must be at least 6 characters", result)
    }

    @Test
    fun `validatePassword - exactly 6 chars is valid`() {
        val result = validator.validatePassword("123456")
        assertNull(result)
    }

    @Test
    fun `validatePassword - long password is valid`() {
        val result = validator.validatePassword("mySecurePassword!")
        assertNull(result)
    }

    // ─── Login Tests ───────────────────────────────────────────────────────────

    @Test
    fun `login - empty email returns error`() {
        val result = validator.login("", "password123")
        assertTrue(result is LoginResult.Error)
        assertEquals("Email cannot be empty", (result as LoginResult.Error).message)
    }

    @Test
    fun `login - invalid email format returns error`() {
        val result = validator.login("notanemail", "password123")
        assertTrue(result is LoginResult.Error)
        assertEquals("Enter a valid email address", (result as LoginResult.Error).message)
    }

    @Test
    fun `login - empty password returns error`() {
        val result = validator.login("user@example.com", "")
        assertTrue(result is LoginResult.Error)
        assertEquals("Password cannot be empty", (result as LoginResult.Error).message)
    }

    @Test
    fun `login - short password returns error`() {
        val result = validator.login("user@example.com", "abc")
        assertTrue(result is LoginResult.Error)
        assertEquals("Password must be at least 6 characters", (result as LoginResult.Error).message)
    }

    @Test
    fun `login - wrong credentials returns error`() {
        val result = validator.login("user@example.com", "wrongpassword")
        assertTrue(result is LoginResult.Error)
        assertEquals("Invalid email or password", (result as LoginResult.Error).message)
    }

    @Test
    fun `login - correct credentials returns success`() {
        val result = validator.login("user@example.com", "password123")
        assertTrue(result is LoginResult.Success)
    }

    @Test
    fun `login - wrong email with correct password returns error`() {
        val result = validator.login("other@example.com", "password123")
        assertTrue(result is LoginResult.Error)
        assertEquals("Invalid email or password", (result as LoginResult.Error).message)
    }
}
