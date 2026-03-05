package com.example.unittestingproject

sealed class OtpResult {
    object Success : OtpResult()
    data class Error(val message: String) : OtpResult()
}

class OtpValidator {

    fun validate(otp: String): String? {
        if (otp.isBlank()) return "OTP cannot be empty"
        if (otp.length != 6) return "OTP must be 6 digits"
        if (!otp.all { it.isDigit() }) return "OTP must contain only digits"
        return null
    }

    fun verify(otp: String): OtpResult {
        val error = validate(otp)
        if (error != null) return OtpResult.Error(error)
        // Simulated OTP check — in a real app this calls the server
        return if (otp == "123456") {
            OtpResult.Success
        } else {
            OtpResult.Error("Invalid OTP. Please try again.")
        }
    }
}
