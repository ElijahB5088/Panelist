package com.nextpanel.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val Paper = Color(0xFFF7F1E8)
private val Ink = Color(0xFF1B1B1B)
private val Red = Color(0xFFE6533C)
private val Mustard = Color(0xFFE8B84A)
private val Sage = Color(0xFF6D8B74)
private val Night = Color(0xFF171717)
private val NightSurface = Color(0xFF252525)

private val LightColors = lightColorScheme(
    primary = Red,
    onPrimary = Color.White,
    secondary = Sage,
    onSecondary = Color.White,
    tertiary = Mustard,
    background = Paper,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = Color(0xFFE9E0D3),
    onSurfaceVariant = Color(0xFF5F584E)
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFFF806B),
    onPrimary = Color(0xFF35110B),
    secondary = Color(0xFFA8C4A9),
    tertiary = Color(0xFFFFD477),
    background = Night,
    onBackground = Color(0xFFF4EEE5),
    surface = NightSurface,
    onSurface = Color(0xFFF4EEE5),
    surfaceVariant = Color(0xFF403A34),
    onSurfaceVariant = Color(0xFFD0C5B9)
)

private val PanelistTypography = Typography(
    headlineLarge = androidx.compose.ui.text.TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Black,
        fontSize = 32.sp,
        lineHeight = 36.sp
    ),
    headlineSmall = androidx.compose.ui.text.TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 22.sp,
        lineHeight = 26.sp
    ),
    titleMedium = androidx.compose.ui.text.TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 16.sp
    ),
    bodyLarge = androidx.compose.ui.text.TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontSize = 16.sp,
        lineHeight = 23.sp
    ),
    labelLarge = androidx.compose.ui.text.TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 14.sp
    )
)

@Composable
fun PanelistTheme(
    darkTheme: Boolean = androidx.compose.foundation.isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = PanelistTypography,
        content = content
    )
}