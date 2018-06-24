package main

import (
    apps "./appsinstalled"
    "flag"
    "fmt"
    "io"
    "log"
    "os"
    "strconv"
    "strings"
    "sync"
    "path/filepath"
    "encoding/csv"
    "compress/gzip"
    "sync/atomic"
    "github.com/bradfitz/gomemcache/memcache"
    "github.com/golang/protobuf/proto"
)

/* Struct with all information about device for storing in memcached */
type AppInfo struct {
    dev_type   string
    dev_id     string
    app        Wrapper
}

/* Wrapper for UserApps struct */
type Wrapper struct {
    Apps       []uint32
    Lat        float64
    Lon        float64
}

/* Initilize connection for memcached for each device type aka key */
func initializeConn(addresses map[string]string) map[string]*memcache.Client {
    clients := make(map[string]*memcache.Client, 4)
    for key, value := range(addresses) {
        clients[key] = memcache.New(value)
    }
    return clients
}

/* Function to parse device data from csvreader read lines.
 * After quitting signal, function send Done signal to WaitGroup parseWg. */
func parse(parseCh <-chan []string, ch chan AppInfo, parseWg *sync.WaitGroup, numErrors *uint64) {
    for {
        if line, err := <-parseCh; !err {
            log.Println("ERROR on reading from parseCh")
        } else if len(line) == 0 {
            /* All lines have been send. Quit reading */
            parseWg.Done()
            return
        } else {
            /* Create Wrapper and send it to the channel ch for storing in Memcached */
            var wrapper Wrapper
            var hasErrors = false

            /* Parse coordinates */
            if lat, err := strconv.ParseFloat(line[2], 64); err == nil {
                wrapper.Lat = lat
            } else {
                hasErrors = true
            }

            if lon, err := strconv.ParseFloat(line[3], 64); err == nil {
                wrapper.Lon = lon
            } else {
                hasErrors = true
            }

            /* Parse slice of apps */
            for _, app := range(strings.Split(line[4], ",")) {
                if val, err := strconv.ParseUint(app, 10, 32); err == nil {
                    wrapper.Apps = append(wrapper.Apps, uint32(val))
                } else {
                    hasErrors = true
                }
            }

            if len(line[0]) == 0 || len(line[1]) == 0 {
                hasErrors = true
            }

            /* If there is no errors send AppInfo firther */
            if hasErrors {
                atomic.AddUint64(numErrors, 1)
            } else {
                ch <- AppInfo{line[0], line[1], wrapper}
            }

        }
    }
}

/* Function to proceess AppInfo data to store it to the Memcached storage.
 * After quitting signal function send Done signal to wg WaitGroup */
func process(ch <-chan AppInfo, wg *sync.WaitGroup,
    clients map[string]*memcache.Client, numErrors *uint64) {
    for {
        app := <-ch
        location := app.dev_type
        wrapper := app.app

        /* key to store */
        key := fmt.Sprintf("%s:%s", location, app.dev_id)

        if app.dev_type == "quit" {
            wg.Done()
            return
        }

        /* Marshall UserApps instance to get value to store */
        if data, err := proto.Marshal(
            &apps.UserApps{Apps: wrapper.Apps, Lat: &wrapper.Lat, Lon: &wrapper.Lon});
            err == nil {
                if clients[location].Set(&memcache.Item{Key: key, Value: data}) != nil {
                    atomic.AddUint64(numErrors, 1)
                }
        }
    }
}

/* Function to create reader for gzipped tsv files.
 * Each read line send to parseCh channel to further processing */
func readFiles(files []string, parseCh chan<-[]string, numLines, numErrors *uint64) {
    for _, file := range(files) {
        log.Printf("Start processing %s file\n", file)

        /* System call to open file */
        rfile, err := os.Open(file)
        if err != nil {
            log.Fatal(err)
        }
        defer rfile.Close()

        /* Reader for gzipped data */
        greader, err := gzip.NewReader(rfile)
        if err != nil {
            log.Fatal(err)
        }
        defer greader.Close()

        /* High-leve Reader for csv-like data */
        csvreader := csv.NewReader(greader)
        csvreader.Comma = '\t'
        csvreader.FieldsPerRecord = 5

        for {
            *numLines++
            line, err := csvreader.Read()

            /* Check correctness of read line */
            if err != nil {
                if err == io.EOF {
                    *numLines--
                    break
                } else if perr, ok := err.(*csv.ParseError); ok && perr.Err == csv.ErrFieldCount {
                    log.Printf("Incorrect number of fields: %v", line)
                    atomic.AddUint64(numErrors, 1)
                    continue
                }
            }

            /* Send line to futher processing */
            parseCh <- line
        }

        /* Rename processed file */
        os.Rename(file, filepath.Join(filepath.Dir(file), "." + filepath.Base(file)))
    }
}


/************************* MAIN *************************/

func main() {

    /* Parsing arguments from command line */
    workers := flag.Int("workers", 8, "number of memcached loaders and string parsers")
    tsvpath := flag.String("path", "tsv", "path to tsv files")
    idfa := flag.String("idfa", "127.0.0.1:13101", "address:port to memcached client for idfa keys")
    gaid := flag.String("gaid", "127.0.0.1:13102", "address:port to memcached client for gaid keys")
    adid := flag.String("adid", "127.0.0.1:13103", "address:port to memcached client for adid keys")
    dvid := flag.String("dvid", "127.0.0.1:13104", "address:port to memcached client for dvid keys")
    logfile := flag.String("log", "MemcLoad.log", "path to log file")
    flag.Parse()

    /* Define file to log to */
    logTo, ok := os.OpenFile(*logfile, os.O_WRONLY | os.O_CREATE | os.O_APPEND, 0664)
    if ok != nil {
        logTo = os.Stdin
        log.Printf("Cannot log to %s, continue logging to stdin", *logfile)
    }
    log.SetOutput(logTo)

    /* Declare shared variables */
    var files     []string
    var err       error
    var numLines  uint64
    var numErrors uint64

    /* Find files for processing */
    log.Printf("Start working in %s path with %v workers\n", *tsvpath, *workers)
    if files, err = filepath.Glob(*tsvpath + "/[^\\.]*\\.tsv\\.gz"); err != nil {
        log.Fatal("Cannot open directory %s for reading", tsvpath)
        os.Exit(1)
    }

    /* Initialize Memcached connections */
    clients := initializeConn(map[string]string{
        "idfa": *idfa, "gaid": *gaid, "adid": *adid, "dvid": *dvid})

    /* Create channels for intercommunication */
    ch := make(chan AppInfo, 1000)
    parseCh := make(chan []string, 1000)

    /* Create WaitGroups to wait until go routines will be finished */
    var wg, parseWg sync.WaitGroup
    wg.Add(*workers)
    parseWg.Add(*workers)
    for i := 0; i < *workers; i ++ {
        go process(ch, &wg, clients, &numErrors)
        go parse(parseCh, ch, &parseWg, &numErrors)
    }

    /* Start reading and processing files */
    readFiles(files, parseCh, &numLines, &numErrors)

    /* Send quit signals by channels to workers */
    for i := 0; i < *workers; i++ {
        ch <- AppInfo{"quit", "", Wrapper{}}
        parseCh <- make([]string, 0)
    }

    /* Close channels and wait until all routines will be finished */
    close(parseCh)
    parseWg.Wait()
    close(ch)
    wg.Wait()

    log.Printf("Error rate is %.2f", float64(numErrors) / float64(numLines))
    log.Println("Finish processing")
}

