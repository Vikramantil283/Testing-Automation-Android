package com.example.unittestingproject

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout

class LoginActivity : AppCompatActivity() {

    private val validator = LoginValidator()
    private val forgotPasswordManager = ForgotPasswordManager()

    private lateinit var tilEmail: TextInputLayout
    private lateinit var tilPassword: TextInputLayout
    private lateinit var etEmail: TextInputEditText
    private lateinit var etPassword: TextInputEditText
    private lateinit var btnLogin: Button
    private lateinit var tvError: TextView
    private lateinit var tvForgotPassword: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        tilEmail         = findViewById(R.id.tilEmail)
        tilPassword      = findViewById(R.id.tilPassword)
        etEmail          = findViewById(R.id.etEmail)
        etPassword       = findViewById(R.id.etPassword)
        btnLogin         = findViewById(R.id.btnLogin)
        tvError          = findViewById(R.id.tvError)
        tvForgotPassword = findViewById(R.id.tvForgotPassword)

        btnLogin.setOnClickListener { handleLogin() }
        tvForgotPassword.setOnClickListener { showForgotPasswordDialog() }
    }

    private fun handleLogin() {
        val email    = etEmail.text.toString().trim()
        val password = etPassword.text.toString()

        tilEmail.error    = null
        tilPassword.error = null
        tvError.visibility = View.GONE

        val emailError    = validator.validateEmail(email)
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
                OtpBottomSheetFragment.newInstance(email)
                    .show(supportFragmentManager, "OtpBottomSheet")
            }
            is LoginResult.Error -> {
                tvError.text = result.message
                tvError.visibility = View.VISIBLE
            }
        }
    }

    private fun showForgotPasswordDialog() {
        val dialogView = layoutInflater.inflate(R.layout.dialog_forgot_password, null)
        val tilDialogEmail = dialogView.findViewById<TextInputLayout>(R.id.tilDialogEmail)
        val etDialogEmail  = dialogView.findViewById<TextInputEditText>(R.id.etDialogEmail)

        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.dialog_forgot_title)
            .setMessage(R.string.dialog_forgot_message)
            .setView(dialogView)
            .setNegativeButton(R.string.dialog_forgot_cancel, null)
            .setPositiveButton(R.string.dialog_forgot_send, null) // set null to prevent auto-dismiss
            .create()

        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val email = etDialogEmail.text.toString().trim()
                when (val result = forgotPasswordManager.sendPasswordReset(email)) {
                    is ForgotPasswordResult.Success -> {
                        dialog.dismiss()
                        Toast.makeText(
                            this,
                            getString(R.string.toast_password_sent),
                            Toast.LENGTH_LONG
                        ).show()
                    }
                    is ForgotPasswordResult.Error -> {
                        tilDialogEmail.error = result.message
                    }
                }
            }
        }

        dialog.show()
    }
}
