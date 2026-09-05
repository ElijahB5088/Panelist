package com.panelist.app.data.api

import com.panelist.app.data.session.SessionStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

object ApiFactory {
    fun create(sessionStore: SessionStore, baseUrl: String): PanelistApi {
        val authInterceptor = Interceptor { chain ->
            val token = sessionStore.token()
            val request = chain.request().newBuilder().apply {
                if (token != null) {
                    header("Authorization", "Bearer $token")
                }
            }.build()
            chain.proceed(request)
        }

        return Retrofit.Builder()
        .baseUrl(baseUrl)
            .client(OkHttpClient.Builder().addInterceptor(authInterceptor).build())
        .addConverterFactory(
            MoshiConverterFactory.create(
                Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
            )
        )
        .build()
        .create(PanelistApi::class.java)
    }
}