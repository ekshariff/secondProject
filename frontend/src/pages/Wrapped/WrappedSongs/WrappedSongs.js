import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import './WrappedSongs.css'; // Import the CSS file
import DarkModeToggle from '../../../components/DarkModeToggle/DarkModeToggle';

const WrappedSongs = () => {
  const [songs, setSongs] = useState([]); // State to store songs
  const [loading, setLoading] = useState(true); // State to manage loading
  const [error, setError] = useState(null); // State to handle errors
  const location = useLocation();
  const navigate = useNavigate();

  const wrappedConfig = location.state?.wrappedConfig || {
    name: 'My Wrapped',
    timePeriod: 'medium_term'
  };

  useEffect(() => {
    const fetchTopSongs = async () => {
      try {
        const token = localStorage.getItem('token');

        console.log("Token found:", token);
        console.log("Fetching songs for time period:", wrappedConfig.timePeriod);

        const response = await axios.get("https://secondproject-8lyv.onrender.com/api/top-songs/", {
          headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json',
          },
          params: {
             time_range: wrappedConfig.timePeriod
          }
        });

        setSongs(response.data.top_songs);

        const wrappedData = {
          ...wrappedConfig,
          songs: response.data.top_songs,
          createdAt: new Date().toISOString()
        };

        localStorage.setItem('currentWrapped', JSON.stringify(wrappedData));

        // Add a delay before setting loading to false
        setTimeout(() => {
          setLoading(false);
        }, 1500); // 1.5 seconds delay
      } catch (err) {
        console.error("Error fetching top songs:", err);
        setError(err.response?.data?.error || "Failed to load songs. Please make sure you're logged in.");
        setLoading(false);
      }
    };

    if (wrappedConfig.timePeriod) {
      fetchTopSongs();
    } else {
      navigate('/selection'); // Redirect if no time period is specified
    }
  }, [wrappedConfig.timePeriod, navigate]);

  const getTimeRangeLabel = (timeRange) => {
    const labels = {
      'short_term': 'Last 4 Weeks',
      'medium_term': 'Last 6 Months',
      'long_term': 'All Time'
    };
    return labels[timeRange] || timeRange;
  };

  if (loading) return <div className='song-loading'><h2>Let's look at your songs first...</h2></div>;
  if (error) return <div>{error}</div>; // Show error state

  return (
    <div className="container">
      <div className="header">
        <div className="title-container">
        <h1 className="title">Your Top Songs</h1>
        </div>
        <Link
          to="/profile"
          className="exit-button"
          onClick={() => console.log("Exit clicked")}
        >
          &times;
        </Link>
      </div>

      <div className="wrapper">
        <div className="song-grid">
          {songs.map((song, index) => (
            <motion.div
              key={index}
              className="song-item"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.2, duration: 0.5 }}
              whileHover={{ scale: 1.05, transition: { duration: 0.01 } }}
              whileTap={{ scale: 0.95 }}
            >
              <img
                src={song.cover_image || "https://via.placeholder.com/161x161"}
                alt={`${song.title} cover`}
                className="song-cover"
              />
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div className="rank">{index + 1}</div>
                <div className="song-title">{song.song_title}</div>
                <div className="artist">{song.artist_name}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      <Link
        to="/top-genres"
        className="next-button"
        onClick={() => console.log("Next page clicked")}
        state={{ wrappedConfig }}
      >
        &#8594;
      </Link>
      <DarkModeToggle />
    </div>
  );
};

export default WrappedSongs;
