package com.example.unittestingproject

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class DashboardActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dashboard)

        val email = intent.getStringExtra(EXTRA_EMAIL) ?: "user@example.com"

        // Avatar: first letter of email, uppercase
        findViewById<TextView>(R.id.tvAvatar).text = email.first().uppercaseChar().toString()
        findViewById<TextView>(R.id.tvUserEmail).text = email

        findViewById<TextView>(R.id.tvLogout).setOnClickListener {
            val intent = Intent(this, LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
        }
    }

    companion object {
        const val EXTRA_EMAIL = "extra_email"
    }
}
