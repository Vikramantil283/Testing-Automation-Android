package com.example.unittestingproject

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout

class LoginActivity : AppCompatActivity() {

    private val validator = LoginValidator()

    private lateinit var tilEmail: TextInputLayout
    private lateinit var tilPassword: TextInputLayout
    private lateinit var etEmail: TextInputEditText
    private lateinit var etPassword: TextInputEditText
    private lateinit var btnLogin: Button
    private lateinit var tvError: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        tilEmail = findViewById(R.id.tilEmail)
        tilPassword = findViewById(R.id.tilPassword)
        etEmail = findViewById(R.id.etEmail)
        etPassword = findViewById(R.id.etPassword)
        btnLogin = findViewById(R.id.btnLogin)
        tvError = findViewById(R.id.tvError)

        btnLogin.setOnClickListener {
            handleLogin()
        }
    }

    private fun handleLogin() {
        val email = etEmail.text.toString().trim()
        val password = etPassword.text.toString()

        // Clear previous errors
        tilEmail.error = null
        tilPassword.error = null
        tvError.visibility = View.GONE

        val emailError = validator.validateEmail(email)
        val passwordError = validator.validatePassword(password)

        if (emailError != null) {
            tilEmail.error = emailError
            return
        }
        if (passwordError != null) {
            tilPassword.error = passwordError
            return
        }

        when (val result = validator.login(email, password)) {
            is LoginResult.Success -> {
                Toast.makeText(this, "Login successful!", Toast.LENGTH_SHORT).show()
            }
            is LoginResult.Error -> {
                tvError.text = result.message
                tvError.visibility = View.VISIBLE
            }
        }
    }
}