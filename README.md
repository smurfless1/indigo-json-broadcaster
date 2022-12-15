# indigo-json-broadcaster

Let Indigo broadcast device changes as JSON, like a tiny radio station on your network.

This came about because every time I wanted to try a different monitoring experiment, I'd have to figure out how to modify the Indigo python environment with modules I wanted to use, like influx clients and so on. And then I'd have to tell everyone that wanted to use my new plugin how to modify/destroy their Indigo python setup. This was a pain.

And then I thought... but why bother? I can just create a JSON bridge and deal with JSON in any old way I want. So how do I get that out of that environment? Well, I can just broadcast it on the local network and let someone listen in like a radio station.

More importantly, this means that things like feeding influxdb or Kafka or MQTT no longer require you to modify your Indigo python install. Create a multicast listener, accept the JSON, and decide what to do with it as a client process.

This was a good idea.

For instance, my ancient mac mini that runs the interface is not fast. So I compiled a multicast-to-Influx binary in go, installed it in ~/bin and created a plist for it. No more thinking - it just runs. No more environment to manage - it's compiled in. Tadaa!

For instance, I wanted to play with putting the messages on MQTT so I had a stream for a different project. I whipped up a node process to copy the values across. Tadaa!

For instance, I want to learn GraphQL so I can query just the interesting parts of the device structures instead of the whole thing. I can stand up a process to keep state internally and respond to GraphQL queries.

Notice I haven't had to modify Indigo. The data source is this steady no-nonsense language-neutral tick tick tick going in the background. And that's exactly what I wanted.

The port in the Indigo plugin will need to match the port in your client as well. Default is 8087 and is configurable in the UI. The broadcast group is: 224.1.1.1