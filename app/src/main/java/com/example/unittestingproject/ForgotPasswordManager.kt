package com.example.unittestingproject

sealed class ForgotPasswordResult {
    data class Success(val email: String) : ForgotPasswordResult()
    data class Error(val message: String) : ForgotPasswordResult()
}

class ForgotPasswordManager {

    private val emailRegex = Regex("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")

    fun validateEmail(email: String): String? {
        if (email.isBlank()) return "Please enter your email address"
        if (!emailRegex.matches(email)) return "Please enter a valid email address"
        return null
    }

    fun sendPasswordReset(email: String): ForgotPasswordResult {
        val error = validateEmail(email)
        if (error != null) return ForgotPasswordResult.Error(error)
        // In a real app this would call your backend/Firebase
        return ForgotPasswordResult.Success(email)
    }
}
