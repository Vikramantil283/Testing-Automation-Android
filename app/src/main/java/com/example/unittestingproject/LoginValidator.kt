package com.example.unittestingproject

sealed class LoginResult {
    object Success : LoginResult()
    data class Error(val message: String) : LoginResult()
}

class LoginValidator {

    private val emailRegex = Regex("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")

    fun validateEmail(email: String): String? {
        if (email.isBlank()) return "Email cannot be empty"
        if (!emailRegex.matches(email)) return "Enter a valid email address"
        return null
    }

    fun validatePassword(password: String): String? {
        if (password.isBlank()) return "Password cannot be empty"
        if (password.length < 6) return "Password must be at least 6 characters"
        return null
    }

    fun login(email: String, password: String): LoginResult {
        val emailError = validateEmail(email)
        if (emailError != null) return LoginResult.Error(emailError)

        val passwordError = validatePassword(password)
        if (passwordError != null) return LoginResult.Error(passwordError)

        // Simulated credential check
        return if (email == "user@example.com" && password == "password123") {
            LoginResult.Success
        } else {
            LoginResult.Error("Invalid email or password")
        }
    }
}