package com.example.unittestingproject

import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.doesNotExist
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.RootMatchers.isDialog
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LoginActivityTest {

    @get:Rule
    val activityRule = ActivityScenarioRule(LoginActivity::class.java)

    // ─── Login UI Tests ────────────────────────────────────────────────────────

    @Test
    fun validLogin_autofillsAndClicksButton_opensOtpBottomSheet() {
        onView(withId(R.id.etEmail))
            .perform(typeText("user@example.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword))
            .perform(typeText("password123"), closeSoftKeyboard())

        onView(withId(R.id.btnLogin)).perform(click())

        // OTP bottom sheet should appear with the first box visible
        onView(withId(R.id.etOtp1))
            .inRoot(isDialog())
            .check(matches(isDisplayed()))
    }

    @Test
    fun invalidCredentials_showsErrorMessage() {
        onView(withId(R.id.etEmail))
            .perform(typeText("user@example.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword))
            .perform(typeText("wrongpassword"), closeSoftKeyboard())

        onView(withId(R.id.btnLogin)).perform(click())

        onView(withId(R.id.tvError))
            .check(matches(isDisplayed()))
        onView(withId(R.id.tvError))
            .check(matches(withText("Invalid email or password")))
    }

    @Test
    fun emptyEmail_showsEmailFieldError() {
        onView(withId(R.id.etPassword))
            .perform(typeText("password123"), closeSoftKeyboard())

        onView(withId(R.id.btnLogin)).perform(click())

        onView(withId(R.id.tilEmail))
            .check(matches(hasDescendant(withText("Email cannot be empty"))))
    }

    @Test
    fun emptyPassword_showsPasswordFieldError() {
        onView(withId(R.id.etEmail))
            .perform(typeText("user@example.com"), closeSoftKeyboard())

        onView(withId(R.id.btnLogin)).perform(click())

        onView(withId(R.id.tilPassword))
            .check(matches(hasDescendant(withText("Password cannot be empty"))))
    }

    @Test
    fun invalidEmailFormat_showsEmailFieldError() {
        onView(withId(R.id.etEmail))
            .perform(typeText("notanemail"), closeSoftKeyboard())
        onView(withId(R.id.etPassword))
            .perform(typeText("password123"), closeSoftKeyboard())

        onView(withId(R.id.btnLogin)).perform(click())

        onView(withId(R.id.tilEmail))
            .check(matches(hasDescendant(withText("Enter a valid email address"))))
    }

    @Test
    fun shortPassword_showsPasswordFieldError() {
        onView(withId(R.id.etEmail))
            .perform(typeText("user@example.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword))
            .perform(typeText("abc"), closeSoftKeyboard())

        onView(withId(R.id.btnLogin)).perform(click())

        onView(withId(R.id.tilPassword))
            .check(matches(hasDescendant(withText("Password must be at least 6 characters"))))
    }

    // ─── OTP Flow Tests ────────────────────────────────────────────────────────

    @Test
    fun validLogin_correctOtp_dismissesBottomSheet() {
        // Step 1: Login with valid credentials
        onView(withId(R.id.etEmail))
            .perform(typeText("user@example.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword))
            .perform(typeText("password123"), closeSoftKeyboard())
        onView(withId(R.id.btnLogin)).perform(click())

        // Step 2: Auto-fill each OTP box (correct OTP: 123456)
        onView(withId(R.id.etOtp1)).inRoot(isDialog()).perform(click(), typeText("1"))
        onView(withId(R.id.etOtp2)).inRoot(isDialog()).perform(click(), typeText("2"))
        onView(withId(R.id.etOtp3)).inRoot(isDialog()).perform(click(), typeText("3"))
        onView(withId(R.id.etOtp4)).inRoot(isDialog()).perform(click(), typeText("4"))
        onView(withId(R.id.etOtp5)).inRoot(isDialog()).perform(click(), typeText("5"))
        onView(withId(R.id.etOtp6)).inRoot(isDialog()).perform(click(), typeText("6"), closeSoftKeyboard())

        // Step 3: Click Verify
        onView(withId(R.id.btnVerifyOtp)).inRoot(isDialog()).perform(click())

        // Step 4: Bottom sheet dismissed — OTP boxes no longer exist
        onView(withId(R.id.etOtp1)).check(doesNotExist())
    }

    @Test
    fun validLogin_wrongOtp_showsOtpError() {
        // Step 1: Login with valid credentials
        onView(withId(R.id.etEmail))
            .perform(typeText("user@example.com"), closeSoftKeyboard())
        onView(withId(R.id.etPassword))
            .perform(typeText("password123"), closeSoftKeyboard())
        onView(withId(R.id.btnLogin)).perform(click())

        // Step 2: Auto-fill wrong OTP
        onView(withId(R.id.etOtp1)).inRoot(isDialog()).perform(click(), typeText("9"))
        onView(withId(R.id.etOtp2)).inRoot(isDialog()).perform(click(), typeText("9"))
        onView(withId(R.id.etOtp3)).inRoot(isDialog()).perform(click(), typeText("9"))
        onView(withId(R.id.etOtp4)).inRoot(isDialog()).perform(click(), typeText("9"))
        onView(withId(R.id.etOtp5)).inRoot(isDialog()).perform(click(), typeText("9"))
        onView(withId(R.id.etOtp6)).inRoot(isDialog()).perform(click(), typeText("9"), closeSoftKeyboard())

        // Step 3: Click Verify
        onView(withId(R.id.btnVerifyOtp)).inRoot(isDialog()).perform(click())

        // Step 4: Error message shown inside the bottom sheet
        onView(withId(R.id.tvOtpError))
            .inRoot(isDialog())
            .check(matches(isDisplayed()))
        onView(withId(R.id.tvOtpError))
            .inRoot(isDialog())
            .check(matches(withText("Invalid OTP. Please try again.")))
    }
}
