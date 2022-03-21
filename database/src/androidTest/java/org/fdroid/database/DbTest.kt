package org.fdroid.database

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.After
import org.junit.Before
import org.junit.runner.RunWith
import java.io.IOException

@RunWith(AndroidJUnit4::class)
abstract class DbTest {

    internal lateinit var repoDao: RepositoryDaoInt
    internal lateinit var appDao: AppDaoInt
    internal lateinit var versionDao: VersionDaoInt
    internal lateinit var db: FDroidDatabaseInt

    @Before
    fun createDb() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        db = Room.inMemoryDatabaseBuilder(context, FDroidDatabaseInt::class.java).build()
        repoDao = db.getRepositoryDao()
        appDao = db.getAppDao()
        versionDao = db.getVersionDaoInt()
    }

    @After
    @Throws(IOException::class)
    fun closeDb() {
        db.close()
    }

}